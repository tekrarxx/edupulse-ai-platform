"""§83: correlation id middleware and the /metrics endpoint."""
import uuid

from fastapi.testclient import TestClient


def test_response_carries_a_generated_request_id_when_none_supplied(client: TestClient) -> None:
    response = client.get("/health")
    assert response.headers["X-Request-ID"]  # non-empty


def test_response_echoes_a_caller_supplied_request_id(client: TestClient) -> None:
    custom_id = f"trace-{uuid.uuid4().hex}"
    response = client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.headers["X-Request-ID"] == custom_id


def test_metrics_endpoint_exposes_prometheus_format(client: TestClient) -> None:
    client.get("/health")  # generate at least one sample first

    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "http_requests_total" in response.text
    assert 'route="/health"' in response.text


def test_unmatched_path_is_labeled_generically_not_with_the_raw_path(client: TestClient) -> None:
    """§109/§139 cardinality-cost discipline applied to metrics: a scanned/
    probed path must never become its own metric label series."""
    bogus_path = f"/does-not-exist-{uuid.uuid4().hex}"
    response = client.get(bogus_path)
    assert response.status_code == 404

    metrics_text = client.get("/metrics").text
    assert bogus_path not in metrics_text
    assert 'route="unmatched"' in metrics_text


def test_error_responses_still_carry_a_request_id_header(client: TestClient) -> None:
    """The middleware sets the header on every response regardless of
    status code — a 401 here is just a convenient, deterministic error to
    trigger without needing a real unhandled 500. The 500-specific body
    field (app/main.py's unhandled_exception_handler) is a separate,
    narrower behavior not exercised by this test."""
    response = client.get("/dashboard/student")
    assert response.status_code == 401
    assert response.headers["X-Request-ID"]
