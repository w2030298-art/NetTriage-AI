"""Integration tests for Step 40 — Classify API with FakeLLMClient."""

from fastapi.testclient import TestClient


def test_classify_returns_200(test_client: TestClient) -> None:
    """POST /api/v1/classify with valid description should return 200."""
    payload = {
        "description": "Network latency is high on the east coast cluster.",
        "ticket_id": "T-001",
        "source": "monitoring",
        "customer_region": "us-east",
    }
    response = test_client.post("/api/v1/classify", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["primary_category"] == "HIGH_LATENCY"
    assert "BANDWIDTH_DEGRADATION" in data["secondary_categories"]
    assert data["confidence"] == 0.85
    assert data["llm_model"] == "fake-model"
    assert data["ticket_id"] == "T-001"
    assert data["source"] == "monitoring"
    assert data["customer_region"] == "us-east"
    assert "record_id" in data
    assert "processed_at" in data


def test_classify_without_optional_fields(test_client: TestClient) -> None:
    """POST /api/v1/classify with minimal required payload should work."""
    payload = {"description": "A simple network issue description for testing."}
    response = test_client.post("/api/v1/classify", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["primary_category"] == "HIGH_LATENCY"
    assert data["confidence"] == 0.85
