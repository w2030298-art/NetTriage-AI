"""BatchJob repository — Module D Step 18."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlmodel import Session, select

from nettriage.db.models import BatchJob


class BatchNotFoundError(Exception):
    """Raised when a :class:`BatchJob` cannot be found by *batch_id*."""


@dataclass
class BatchJobCreate:
    """Input data for creating a :class:`BatchJob`."""

    batch_id: str
    input_filename: str
    stored_input_path: str


class BatchRepository:
    """Data-access layer for :class:`BatchJob`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------------ helpers

    def _get_or_raise(self, batch_id: str) -> BatchJob:
        """Retrieve a batch by id; raise :class:`BatchNotFoundError` if missing."""
        batch = self.get_by_batch_id(batch_id)
        if batch is None:
            raise BatchNotFoundError(f"BatchJob with batch_id={batch_id!r} not found")
        return batch

    # ------------------------------------------------------------------ public API

    def create_batch(self, data: BatchJobCreate) -> BatchJob:
        """Persist a new batch job."""
        job = BatchJob(**vars(data))
        self._session.add(job)
        self._session.commit()
        self._session.refresh(job)
        return job

    def get_by_batch_id(self, batch_id: str) -> BatchJob | None:
        """Return the batch identified by *batch_id* or ``None``."""
        stmt = select(BatchJob).where(BatchJob.batch_id == batch_id)
        return self._session.exec(stmt).first()

    def mark_running(self, batch_id: str, total_rows: int) -> None:
        """Transition the batch to RUNNING and record *total_rows*."""
        batch = self._get_or_raise(batch_id)
        batch.status = "RUNNING"
        batch.total_rows = total_rows
        batch.started_at = datetime.now()
        self._session.add(batch)
        self._session.commit()

    def increment_progress(
        self,
        batch_id: str,
        success_delta: int = 0,
        failed_delta: int = 0,
        review_required_delta: int = 0,
    ) -> None:
        """Atomically bump counter columns on the target batch."""
        batch = self._get_or_raise(batch_id)
        batch.processed_rows += success_delta + failed_delta
        batch.success_rows += success_delta
        batch.failed_rows += failed_delta
        batch.review_required_rows += review_required_delta
        self._session.add(batch)
        self._session.commit()

    def mark_completed(self, batch_id: str, output_path: str) -> None:
        """Mark the batch as COMPLETED with an *output_path*."""
        batch = self._get_or_raise(batch_id)
        batch.status = "COMPLETED"
        batch.output_path = output_path
        batch.completed_at = datetime.now()
        self._session.add(batch)
        self._session.commit()

    def mark_partial_failed(
        self,
        batch_id: str,
        output_path: str,
        error_message: str | None = None,
    ) -> None:
        """Mark the batch as PARTIAL_FAILED (partial success)."""
        batch = self._get_or_raise(batch_id)
        batch.status = "PARTIAL_FAILED"
        batch.output_path = output_path
        batch.error_message = error_message
        batch.completed_at = datetime.now()
        self._session.add(batch)
        self._session.commit()

    def mark_failed(self, batch_id: str, error_message: str) -> None:
        """Mark the batch as FAILED with an *error_message*."""
        batch = self._get_or_raise(batch_id)
        batch.status = "FAILED"
        batch.error_message = error_message
        batch.completed_at = datetime.now()
        self._session.add(batch)
        self._session.commit()
