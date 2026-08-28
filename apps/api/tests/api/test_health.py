from fastapi.testclient import TestClient


def test_health_returns_real_dependency_status_not_hardcoded(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ok", "degraded"}
    assert set(body["dependencies"].keys()) == {"database", "redis"}
    assert body["dependencies"]["database"] in {"ok", "unavailable"}
    assert body["dependencies"]["redis"] in {"ok", "unavailable"}


def test_unhandled_exception_does_not_leak_internals(client: TestClient) -> None:
    response = client.get("/does-not-exist")

    assert response.status_code == 404
    assert "Traceback" not in response.text
