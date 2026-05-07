"""Integration tests for Step 41 — Batch API with FakeLLMClient. [scope:review]"""

import io
from typing import TYPE_CHECKING

from fastapi.testclient import TestClient

if TYPE_CHECKING:
    pass


_CSV_CONTENT = "description,ticket_id\nNetwork latency is high on east coast cluster,T-001\n"


def test_create_batch_returns_201(test_client: TestClient) -> None:
    """POST /api/v1/batches with a valid CSV should return 201."""
    response = test_client.post(
        "/api/v1/batches",
        files={"file": ("test.csv", io.BytesIO(_CSV_CONTENT.encode()), "text/csv")},
    )
    assert response.status_code == 201, response.text
    data = response.json()

    assert "batch_id" in data
    assert data["status"] == "PENDING"
    assert data["message"] == "Batch created and queued for processing"
    assert data["received_rows"] == 0


def test_get_batch_status_returns_200(test_client: TestClient) -> None:
    """GET /api/v1/batches/{batch_id} should return status after creation."""
    create_resp = test_client.post(
        "/api/v1/batches",
        files={"file": ("test.csv", io.BytesIO(_CSV_CONTENT.encode()), "text/csv")},
    )
    assert create_resp.status_code == 201
    batch_id = create_resp.json()["batch_id"]

    response = test_client.get(f"/api/v1/batches/{batch_id}")
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["batch_id"] == batch_id
    assert data["status"] in ("PENDING", "RUNNING", "COMPLETED")
    assert "total_rows" in data
    assert "processed_rows" in data


def test_get_batch_not_found_returns_api_error(test_client: TestClient) -> None:
    """GET /api/v1/batches/nonexistent should return error response."""
    response = test_client.get("/api/v1/batches/nonexistent-batch-id")
    assert response.status_code in (404, 500)
