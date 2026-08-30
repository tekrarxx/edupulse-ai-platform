"""§83/§84: structured logging, request-id stamping, and secret redaction."""
import json
import logging

from app.core.logging import JsonFormatter, RedactSensitiveFieldsFilter, RequestIdFilter
from app.core.request_context import get_request_id, set_request_id


def _make_record(msg: str, args: tuple = ()) -> logging.LogRecord:
    return logging.LogRecord(name="test", level=logging.INFO, pathname="", lineno=0, msg=msg, args=args, exc_info=None)


def test_json_formatter_produces_valid_json_with_expected_fields() -> None:
    record = _make_record("hello world")
    payload = json.loads(JsonFormatter().format(record))

    assert payload["message"] == "hello world"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "test"
    assert "timestamp" in payload
    assert "request_id" in payload


def test_json_formatter_merges_extra_fields() -> None:
    record = _make_record("request")
    record.http_method = "GET"
    record.http_route = "/health"
    record.duration_ms = 12.5

    payload = json.loads(JsonFormatter().format(record))
    assert payload["http_method"] == "GET"
    assert payload["http_route"] == "/health"
    assert payload["duration_ms"] == 12.5


def test_request_id_filter_stamps_current_contextvar_value() -> None:
    set_request_id("test-request-id-123")
    record = _make_record("hello")

    assert RequestIdFilter().filter(record) is True
    assert record.request_id == "test-request-id-123"

    payload = json.loads(JsonFormatter().format(record))
    assert payload["request_id"] == "test-request-id-123"


def test_request_id_defaults_to_placeholder_outside_a_request() -> None:
    set_request_id("-")
    assert get_request_id() == "-"


def test_redact_filter_hides_password_shaped_messages() -> None:
    record = _make_record('login attempt password="hunter2"')
    assert RedactSensitiveFieldsFilter().filter(record) is True
    assert record.msg == "[redacted: potential sensitive field in log message]"


def test_redact_filter_leaves_ordinary_messages_untouched() -> None:
    record = _make_record("decision generated for skill %s", ("skill-123",))
    assert RedactSensitiveFieldsFilter().filter(record) is True
    assert record.msg == "decision generated for skill %s"
