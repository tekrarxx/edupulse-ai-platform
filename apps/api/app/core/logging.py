import json
import logging
import sys

from app.core.request_context import get_request_id

_SENSITIVE_KEYS = {"password", "token", "secret", "authorization", "api_key"}


class RedactSensitiveFieldsFilter(logging.Filter):
    """Defense-in-depth: refuses to emit a record whose message text contains
    an obvious secret-shaped key=value pair (§84 — never log passwords,
    tokens, API keys, or learner-sensitive data)."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage().lower()
        for key in _SENSITIVE_KEYS:
            if f"{key}=" in message or f'"{key}"' in message:
                record.msg = "[redacted: potential sensitive field in log message]"
                record.args = ()
                break
        return True


class RequestIdFilter(logging.Filter):
    """Stamps every log record with the current request's correlation id
    (app/core/request_context.py) — "-" for log lines emitted outside a
    request (startup, background work), never a fabricated value."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


_STANDARD_RECORD_ATTRS = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {"message", "asctime", "request_id"}


class JsonFormatter(logging.Formatter):
    """§83 structured logs: one JSON object per line, parseable by any log
    aggregator, instead of the positional plain-text format this replaces.
    Any caller-supplied `extra={...}` field (e.g. the access-log middleware's
    http_method/http_route/duration_ms) is merged in verbatim — the standard
    idiom for structured logging with the stdlib `logging` module.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_RECORD_ATTRS:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(environment: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RedactSensitiveFieldsFilter())
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.DEBUG if environment == "development" else logging.INFO)
