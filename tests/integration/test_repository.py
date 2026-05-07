"""Integration tests for TicketRepository and BatchRepository — Module D Step 19."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import cast

import pytest
from sqlmodel import Session, create_engine  # type: ignore[import-untyped]

from nettriage.db.init_db import init_db
from nettriage.repositories.batch_repository import (
    BatchJobCreate,
    BatchNotFoundError,
    BatchRepository,
)
from nettriage.repositories.ticket_repository import TicketRecordCreate, TicketRepository
from nettriage.schemas.enums import FaultCategory
from nettriage.schemas.ticket import TicketQueryFilters


@pytest.fixture
def temp_db() -> str:
    """Create a temporary SQLite database file and return its path."""
    fd, path = tempfile.mkstemp(suffix=".db", prefix="nettriage_test_")
    os.close(fd)
    yield path
    # Cleanup: remove db + WAL/SHM files
    for suffix in ("", "-wal", "-shm"):
        p = Path(path + suffix)
        if p.exists():
            p.unlink()


@pytest.fixture
def engine(temp_db: str):
    """Create an engine connected to the temp database, init tables, then dispose."""
    engine = create_engine(f"sqlite:///{temp_db}", connect_args={"check_same_thread": False})
    init_db(engine)
    yield engine
    engine.dispose()


# ------------------------------------------------------------------ TicketRepository


def test_create_and_get_ticket(engine) -> None:  # type: ignore[no-untyped-def]
    """Create a ticket and retrieve it by id."""
    with Session(engine) as session:
        repo = TicketRepository(session)
        data = TicketRecordCreate(
            ticket_id="TKT-001",
            batch_id="BATCH-01",
            description_text="Slow Wi-Fi in zone 3",
            primary_category="HIGH_LATENCY",
            confidence=0.92,
            review_required=True,
        )
        record = repo.create_result(data)
        assert record.id is not None

        fetched = repo.get_by_id(record.id)  # type: ignore[arg-type]
        assert fetched is not None
        assert fetched.ticket_id == "TKT-001"
        assert fetched.primary_category == "HIGH_LATENCY"


def test_get_nonexistent_ticket(engine) -> None:  # type: ignore[no-untyped-def]
    """get_by_id returns None for missing record."""
    with Session(engine) as session:
        repo = TicketRepository(session)
        assert repo.get_by_id(99999) is None


def test_list_tickets_with_filters(engine) -> None:  # type: ignore[no-untyped-def]
    """Query tickets via TicketQueryFilters."""
    with Session(engine) as session:
        repo = TicketRepository(session)

        # Insert helpers
        def _make(ticket_id: str, category: str, desc: str, batch_id: str = "B1") -> None:
            repo.create_result(
                TicketRecordCreate(
                    ticket_id=ticket_id,
                    batch_id=batch_id,
                    primary_category=category,
                    description_text=desc,
                )
            )

        _make("T-1", "COVERAGE_ISSUE", "no signal")
        _make("T-2", "HIGH_LATENCY", "slow network")
        _make("T-3", "HIGH_LATENCY", "latency spike")

    with Session(engine) as session:
        repo = TicketRepository(session)

        # Filter by primary_category
        filters = TicketQueryFilters(primary_category=FaultCategory.HIGH_LATENCY)
        results = repo.list_results(filters)
        assert len(results) == 2

        # Keyword search
        filters = TicketQueryFilters(keyword="signal")
        results = repo.list_results(filters)
        assert len(results) == 1
        assert results[0].ticket_id == "T-1"

        # Limit + offset
        filters = TicketQueryFilters(limit=1, offset=1)
        results = repo.list_results(filters)
        assert len(results) == 1


def test_update_review_status(engine) -> None:  # type: ignore[no-untyped-def]
    """update_review_status changes review fields."""
    with Session(engine) as session:
        repo = TicketRepository(session)
        record = repo.create_result(
            TicketRecordCreate(ticket_id="REV-1", primary_category="UNKNOWN")
        )

    with Session(engine) as session:
        repo = TicketRepository(session)
        updated = repo.update_review_status(
            cast(int, record.id),
            review_status="CONFIRMED",
            reviewed_category="COVERAGE_ISSUE",
            review_note="verified by agent",
        )
        assert updated.review_status == "CONFIRMED"
        assert updated.reviewed_category == "COVERAGE_ISSUE"
        assert updated.review_note == "verified by agent"


# ------------------------------------------------------------------ BatchRepository


def test_create_and_get_batch(engine) -> None:  # type: ignore[no-untyped-def]
    """Create a batch and retrieve it."""
    with Session(engine) as session:
        repo = BatchRepository(session)
        job = repo.create_batch(
            BatchJobCreate(
                batch_id="B-001",
                input_filename="input.csv",
                stored_input_path="/tmp/input.csv",
            )
        )
        assert job.id is not None
        assert job.status == "PENDING"

        fetched = repo.get_by_batch_id("B-001")
        assert fetched is not None
        assert fetched.batch_id == "B-001"


def test_batch_lifecycle(engine) -> None:  # type: ignore[no-untyped-def]
    """Full batch lifecycle: running → progress → completed."""
    with Session(engine) as session:
        repo = BatchRepository(session)
        repo.create_batch(
            BatchJobCreate(
                batch_id="B-LIFECYCLE",
                input_filename="data.csv",
                stored_input_path="/tmp/data.csv",
            )
        )

    with Session(engine) as session:
        repo = BatchRepository(session)
        repo.mark_running("B-LIFECYCLE", total_rows=100)
        batch = repo.get_by_batch_id("B-LIFECYCLE")
        assert batch is not None
        assert batch.status == "RUNNING"
        assert batch.total_rows == 100

    with Session(engine) as session:
        repo = BatchRepository(session)
        repo.increment_progress(
            "B-LIFECYCLE", success_delta=2, failed_delta=1, review_required_delta=1
        )
        batch = repo.get_by_batch_id("B-LIFECYCLE")
        assert batch is not None
        assert batch.processed_rows == 3
        assert batch.success_rows == 2
        assert batch.failed_rows == 1
        assert batch.review_required_rows == 1

    with Session(engine) as session:
        repo = BatchRepository(session)
        repo.mark_completed("B-LIFECYCLE", "/tmp/output.csv")
        batch = repo.get_by_batch_id("B-LIFECYCLE")
        assert batch is not None
        assert batch.status == "COMPLETED"
        assert batch.output_path == "/tmp/output.csv"


def test_mark_partial_failed(engine) -> None:  # type: ignore[no-untyped-def]
    """mark_partial_failed sets status and optional error."""
    with Session(engine) as session:
        repo = BatchRepository(session)
        repo.create_batch(
            BatchJobCreate(
                batch_id="B-PARTIAL",
                input_filename="f.csv",
                stored_input_path="/tmp/f.csv",
            )
        )

    with Session(engine) as session:
        repo = BatchRepository(session)
        repo.mark_partial_failed("B-PARTIAL", "/tmp/partial.csv", error_message="3 rows failed")
        batch = repo.get_by_batch_id("B-PARTIAL")
        assert batch is not None
        assert batch.status == "PARTIAL_FAILED"
        assert batch.output_path == "/tmp/partial.csv"
        assert batch.error_message == "3 rows failed"


def test_mark_failed(engine) -> None:  # type: ignore[no-untyped-def]
    """mark_failed sets FAILED status."""
    with Session(engine) as session:
        repo = BatchRepository(session)
        repo.create_batch(
            BatchJobCreate(
                batch_id="B-FAIL",
                input_filename="bad.csv",
                stored_input_path="/tmp/bad.csv",
            )
        )

    with Session(engine) as session:
        repo = BatchRepository(session)
        repo.mark_failed("B-FAIL", "CSV parse error")
        batch = repo.get_by_batch_id("B-FAIL")
        assert batch is not None
        assert batch.status == "FAILED"
        assert batch.error_message == "CSV parse error"


def test_batch_not_found_raises(engine) -> None:  # type: ignore[no-untyped-def]
    """Operations on a missing batch_id raise BatchNotFoundError."""
    with Session(engine) as session:
        repo = BatchRepository(session)
        with pytest.raises(BatchNotFoundError):
            repo.mark_running("NO-EXIST", 10)
        with pytest.raises(BatchNotFoundError):
            repo.mark_completed("NO-EXIST", "/x")
        with pytest.raises(BatchNotFoundError):
            repo.mark_failed("NO-EXIST", "oops")
