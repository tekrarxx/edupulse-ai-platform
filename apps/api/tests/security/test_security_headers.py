"""§78 baseline security headers, applied globally by
app/main.py::security_headers_middleware. One representative endpoint is
enough — the assertion is about the middleware, not any particular route.
"""
from fastapi.testclient import TestClient


def test_response_carries_baseline_security_headers(client: TestClient) -> None:
    response = client.get("/health")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["Content-Security-Policy"] == "default-src 'none'"
    assert "Strict-Transport-Security" in response.headers
    assert "Permissions-Policy" in response.headers


def test_security_headers_present_even_on_error_responses(client: TestClient) -> None:
    response = client.get("/dashboard/student")  # unauthenticated -> 401

    assert response.status_code == 401
    assert response.headers["X-Content-Type-Options"] == "nosniff"
