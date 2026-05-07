"""Batch processing orchestration service — create, track, and retrieve batch jobs.

Step 39: BatchService
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import BackgroundTasks, UploadFile

from nettriage.batch.csv_processor import CSVProcessor
from nettriage.batch.exporter import ResultCSVExporter
from nettriage.batch.field_mapper import CSVFieldMapper
from nettriage.batch.file_store import BatchFileStore
from nettriage.core.config import Settings
from nettriage.core.security import ensure_within_directory, safe_batch_id
from nettriage.repositories.batch_repository import (
    BatchJobCreate,
    BatchNotFoundError,
    BatchRepository,
)
from nettriage.schemas.batch import BatchCreateResponse, BatchStatusResponse
from nettriage.schemas.enums import BatchStatus
from nettriage.services.classification_service import ClassificationService

logger = logging.getLogger(__name__)


class BatchService:
    """Coordinate batch CSV upload, background processing, and status queries."""

    def __init__(
        self,
        file_store: BatchFileStore,
        batch_repository: BatchRepository,
        classification_service: ClassificationService,
        settings: Settings,
    ) -> None:
        self._file_store = file_store
        self._batch_repo = batch_repository
        self._classification_service = classification_service
        self._settings = settings

    # ------------------------------------------------------------------ public API

    def create_batch(
        self,
        upload_file: UploadFile,
        background_tasks: BackgroundTasks,
    ) -> BatchCreateResponse:
        """Validate the upload, persist the batch job, and schedule processing.

        Args:
            upload_file: The CSV file from the incoming HTTP request.
            background_tasks: FastAPI BackgroundTasks for async processing.

        Returns:
            A :class:`BatchCreateResponse` with the batch ID and initial status.

        Raises:
            ValueError: If the file is not a ``.csv`` or exceeds size limits.
        """
        batch_id = safe_batch_id()

        # Save the uploaded file
        stored_path = self._file_store.save_upload(batch_id, upload_file)

        # Create the batch job record (PENDING)
        job_create = BatchJobCreate(
            batch_id=batch_id,
            input_filename=upload_file.filename or "unknown.csv",
            stored_input_path=str(stored_path),
        )
        self._batch_repo.create_batch(job_create)

        # Schedule background processing
        background_tasks.add_task(
            self._run_processing,
            batch_id=batch_id,
            input_path=stored_path,
        )

        return BatchCreateResponse(
            batch_id=batch_id,
            status=BatchStatus.PENDING,
            received_rows=0,
            message="Batch created and queued for processing",
        )

    def get_batch_status(self, batch_id: str) -> BatchStatusResponse:
        """Return the current status and progress counters for *batch_id*.

        Args:
            batch_id: The batch identifier returned by ``create_batch``.

        Returns:
            A :class:`BatchStatusResponse` with progress fields.

        Raises:
            :class:`BatchNotFoundError`: If *batch_id* does not exist.
        """
        job = self._batch_repo._get_or_raise(batch_id)  # noqa: SLF001  — intentional
        return BatchStatusResponse(
            batch_id=job.batch_id,
            status=BatchStatus(job.status),
            total_rows=job.total_rows,
            processed_rows=job.processed_rows,
            success_rows=job.success_rows,
            failed_rows=job.failed_rows,
            review_required_rows=job.review_required_rows,
            created_at=job.created_at.isoformat() if job.created_at else "",
            completed_at=job.completed_at.isoformat() if job.completed_at else None,
            error_message=job.error_message,
        )

    def get_batch_download_path(self, batch_id: str) -> Path:
        """Resolve and validate the output file path for *batch_id*.

        The returned path is guaranteed to be within the configured export
        directory.

        Args:
            batch_id: The batch identifier.

        Returns:
            Absolute :class:`Path` to the result CSV.

        Raises:
            :class:`ValueError`: If the resolved path escapes the export directory.
            :class:`BatchNotFoundError`: If *batch_id* does not exist or has no output.
        """
        job = self._batch_repo._get_or_raise(batch_id)  # noqa: SLF001

        if not job.output_path:
            raise BatchNotFoundError(
                f"Batch {batch_id!r} has no output file yet"
            )

        catalog_path = Path(job.output_path)
        return ensure_within_directory(self._settings.export_dir, Path(catalog_path.name))

    # ------------------------------------------------------------------ background

    async def _run_processing(self, batch_id: str, input_path: Path) -> None:
        """Background task: run the CSV processor for *batch_id*.

        Creates a fresh :class:`CSVProcessor` with its own database connection
        so the background task is independent of the request lifecycle.
        """
        exporter = ResultCSVExporter(self._settings)
        field_mapper = CSVFieldMapper()
        processor = CSVProcessor(
            classification_service=self._classification_service,
            exporter=exporter,
            field_mapper=field_mapper,
            settings=self._settings,
        )

        try:
            await processor.process_batch(batch_id, input_path)
        except Exception:
            logger.exception(
                "Unhandled error in background batch processing for %s", batch_id
            )
