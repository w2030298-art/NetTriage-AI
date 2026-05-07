"""Integration tests for Step 43 — Minimal HTML UI."""

from fastapi.testclient import TestClient


def test_index_returns_html(test_client: TestClient) -> None:
    """GET / should return an HTML page with 200 status."""
    response = test_client.get("/")
    assert response.status_code == 200, response.text
    content_type = response.headers.get("content-type", "")
    assert "text/html" in content_type
    body = response.text
    assert "<!DOCTYPE html>" in body or "<html" in body
    assert "NetTriage AI" in body
