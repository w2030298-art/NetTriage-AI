"""Step 44: E2E CSV batch flow test — upload, process, poll, download, verify.

Uses FakeLLMClient (never calls real DeepSeek API) via the standard
conftest.py test_client fixture.
"""

from __future__ import annotations

import csv
import io
import time
from pathlib import Path

from fastapi.testclient import TestClient

# Path to fixture CSV files relative to the tests directory.
_FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
_SAMPLE_CSV = _FIXTURES_DIR / "sample_tickets.csv"

# Maximum poll attempts for batch completion
_MAX_POLL_ATTEMPTS = 30
_POLL_INTERVAL_SECONDS = 0.5


def _read_sample_csv_bytes() -> bytes:
    """Read the sample_tickets.csv fixture as UTF-8 bytes."""
    return _SAMPLE_CSV.read_bytes()


def _parse_csv(text: str) -> tuple[list[str], list[list[str]]]:
    """Parse CSV text using csv.reader, returning (header, data_rows)."""
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return [], []
    return rows[0], rows[1:]


_EXPECTED_COLUMNS = [
    "ticket_id",
    "primary_category",
    "secondary_categories",
    "confidence",
    "review_required",
    "review_reasons",
    "key_symptoms",
    "summary",
    "troubleshooting_steps",
    "llm_model",
    "llm_latency_ms",
    "processed_at",
    "error",
]


def test_e2e_upload_sample_csv_and_wait_for_completion(
    test_client: TestClient,
) -> None:
    """Upload sample_tickets.csv, poll until COMPLETED, download and verify output."""
    csv_bytes = _read_sample_csv_bytes()

    # 1. Upload the CSV
    upload_resp = test_client.post(
        "/api/v1/batches",
        files={"file": ("sample_tickets.csv", io.BytesIO(csv_bytes), "text/csv")},
    )
    assert upload_resp.status_code == 201, upload_resp.text
    create_data = upload_resp.json()
    batch_id: str = create_data["batch_id"]
    assert batch_id, "Expected non-empty batch_id"
    assert create_data["status"] == "PENDING"

    # 2. Poll until COMPLETED or PARTIAL_FAILED
    final_status: str | None = None
    for _ in range(_MAX_POLL_ATTEMPTS):
        status_resp = test_client.get(f"/api/v1/batches/{batch_id}")
        assert status_resp.status_code == 200, status_resp.text
        status_data = status_resp.json()

        final_status = status_data["status"]
        if final_status in ("COMPLETED", "PARTIAL_FAILED"):
            break
        time.sleep(_POLL_INTERVAL_SECONDS)
    else:
        msg = (
            f"Batch {batch_id} did not reach COMPLETED/PARTIAL_FAILED within "
            f"{_MAX_POLL_ATTEMPTS * _POLL_INTERVAL_SECONDS}s. "
            f"Last status: {final_status}"
        )
        raise AssertionError(msg)

    # 3. Assert batch-level counters look reasonable
    assert status_data["total_rows"] == 12, (
        f"Expected 12 total rows, got {status_data['total_rows']}"
    )
    assert status_data["processed_rows"] == 12
    assert status_data["success_rows"] >= 1

    # 4. Download result CSV
    download_resp = test_client.get(f"/api/v1/batches/{batch_id}/download")
    assert download_resp.status_code == 200, download_resp.text

    # 5. Parse result CSV with proper CSV reader (handles quoted JSON fields)
    header, data_rows = _parse_csv(download_resp.text)
    assert header, "Result CSV must have a header row"
    assert len(data_rows) == 12, f"Expected 12 data rows, got {len(data_rows)}"

    # Verify all expected columns are present
    for col in _EXPECTED_COLUMNS:
        assert col in header, f"Column {col!r} missing from output CSV header: {header}"

    # Build column index map
    col_idx = {col: i for i, col in enumerate(header)}
    review_idx = col_idx["review_required"]
    ticket_id_idx = col_idx["ticket_id"]

    # 6. Verify at least one row has review_required=True
    review_required_count = 0
    for row in data_rows:
        if len(row) > review_idx and row[review_idx].strip().lower() == "true":
            review_required_count += 1

    assert review_required_count >= 1, (
        "Expected at least one row with review_required=True, got 0. "
        "Check that the review policy triggers for at least one ticket."
    )

    # 7. Verify we have distinct ticket IDs in output
    ticket_ids_in_output = {
        row[ticket_id_idx].strip()
        for row in data_rows
        if len(row) > ticket_id_idx and row[ticket_id_idx].strip()
    }
    assert len(ticket_ids_in_output) >= 1, "Expected at least one ticket_id in output"

    # 8. Each data row should have the correct number of fields
    expected_col_count = len(_EXPECTED_COLUMNS)
    for i, row in enumerate(data_rows, start=1):
        assert len(row) == expected_col_count, (
            f"Row {i} has {len(row)} fields, expected {expected_col_count}"
        )
