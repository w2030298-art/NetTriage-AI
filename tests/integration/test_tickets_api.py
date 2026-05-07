"""Integration tests for Step 42 — Tickets API with FakeLLMClient."""

from fastapi.testclient import TestClient


def test_list_tickets_returns_empty(test_client: TestClient) -> None:
    """GET /api/v1/tickets on a fresh DB should return empty list."""
    response = test_client.get("/api/v1/tickets")
    assert response.status_code == 200, response.text
    data = response.json()
    assert isinstance(data, list)
    assert data == []


def test_list_tickets_with_classified_ticket(test_client: TestClient) -> None:
    """GET /api/v1/tickets should return tickets after classification."""
    payload = {"description": "Network latency on core switch is high."}
    classify_resp = test_client.post("/api/v1/classify", json=payload)
    assert classify_resp.status_code == 200

    response = test_client.get("/api/v1/tickets")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    ticket = data[0]
    assert ticket["primary_category"] == "HIGH_LATENCY"
    assert ticket["confidence"] == 0.85


def test_get_ticket_by_id(test_client: TestClient) -> None:
    """GET /api/v1/tickets/{record_id} should return a single ticket."""
    payload = {"description": "DNS resolution failing for api.example.com."}
    classify_resp = test_client.post("/api/v1/classify", json=payload)
    assert classify_resp.status_code == 200

    list_resp = test_client.get("/api/v1/tickets?limit=1")
    tickets = list_resp.json()
    assert len(tickets) >= 1

    ticket_id = tickets[0]["id"]
    response = test_client.get(f"/api/v1/tickets/{ticket_id}")
    assert response.status_code == 200
    assert response.json()["id"] == ticket_id


def test_patch_review(test_client: TestClient) -> None:
    """PATCH /api/v1/tickets/{record_id}/review should update review status."""
    payload = {"description": "Packet loss observed between DC1 and DC2."}
    classify_resp = test_client.post("/api/v1/classify", json=payload)
    assert classify_resp.status_code == 200

    list_resp = test_client.get("/api/v1/tickets?limit=1")
    tickets = list_resp.json()
    assert len(tickets) >= 1

    record_id = tickets[0]["id"]
    review_payload = {
        "review_status": "CORRECTED",
        "reviewed_category": "PACKET_LOSS",
        "review_note": "Confirmed packet loss by NOC team",
    }
    response = test_client.patch(f"/api/v1/tickets/{record_id}/review", json=review_payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["record_id"] == record_id
    assert data["review_status"] == "CORRECTED"
    assert data["reviewed_category"] == "PACKET_LOSS"
    assert data["review_note"] == "Confirmed packet loss by NOC team"
