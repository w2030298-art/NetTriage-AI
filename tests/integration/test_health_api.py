"""Integration tests for the health check API."""

from fastapi.testclient import TestClient


def test_healthz_returns_200(test_client: TestClient) -> None:
    """GET /healthz should return 200 with status ok."""
    response = test_client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "NetTriage AI"
    assert data["version"] == "0.1.0"
