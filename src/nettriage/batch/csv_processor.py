"""Chunked CSV batch processor — classify rows with per-row error isolation.

Step 38: CSVProcessor  [scope:review]
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from sqlmodel import Session

from nettriage.batch.exporter import ResultCSVExporter
from nettriage.batch.field_mapper import CSVFieldMapper
from nettriage.core.config import Settings
from nettriage.db.session import create_engine_from_settings
from nettriage.repositories.batch_repository import BatchRepository
from nettriage.services.classification_service import ClassificationService

logger = logging.getLogger(__name__)

# CSV-specific error message prefix used when no description column is found.
_CSV_DESCRIPTION_COLUMN_MISSING = (
    "CSV must contain a description column. Recognised names include: "
    "description, desc, content, fault_description, problem_description, ..."
)


class CSVProcessor:
    """Process a batch CSV file row-by-row using chunked reading.

    Design constraints:
    * NEVER holds all results in memory at once — rows are streamed to disk.
    * Per-row error isolation: a single failing row does not stop the batch.
    * Background-safe: creates its own database session internally.
    """

    def __init__(
        self,
        classification_service: ClassificationService,
        exporter: ResultCSVExporter,
        field_mapper: CSVFieldMapper,
        settings: Settings,
    ) -> None:
        self._classification_service = classification_service
        self._exporter = exporter
        self._field_mapper = field_mapper
        self._settings = settings

    # ------------------------------------------------------------------ public API

    async def process_batch(self, batch_id: str, input_path: Path) -> None:
        """Run the full batch classification pipeline for *batch_id*.

        Args:
            batch_id: The unique batch identifier (must have a pending DB record).
            input_path: Absolute path to the uploaded CSV file.
        """
        # 1. Infer field mapping from the CSV header
        try:
            mapping = self._field_mapper.infer_mapping_from_file(input_path)
        except ValueError:
            raise

        desc_col: str = mapping.description_column
        ticket_id_col: str | None = mapping.ticket_id_column

        # 2. Count total rows (quick line-count pass; subtract header)
        with open(input_path, encoding="utf-8") as fh:
            total_rows = sum(1 for _ in fh) - 1
        if total_rows < 0:
            total_rows = 0

        if total_rows > self._settings.max_csv_rows:
            raise ValueError(
                f"CSV has {total_rows} rows, which exceeds the limit "
                f"of {self._settings.max_csv_rows}"
            )

        # 3. Create a fresh database session for background processing
        engine = create_engine_from_settings(self._settings)
        with Session(engine) as session:
            batch_repo = BatchRepository(session)

            # 4. Mark running
            try:
                batch_repo.mark_running(batch_id, total_rows)
            except Exception as exc:
                logger.warning("Failed to mark_running for batch %s: %s", batch_id, exc)

            # 5. Create output file
            output_path = self._exporter.create_output(batch_id)

            # 6. Process in chunks
            total_success = 0
            total_failed = 0
            total_review = 0
            catastrophic_error: str | None = None

            try:
                reader = pd.read_csv(
                    input_path,
                    chunksize=self._settings.csv_chunksize,
                )

                # Validate that the description column actually exists in the data
                peek_df = pd.read_csv(input_path, nrows=0)
                if desc_col not in peek_df.columns:
                    raise ValueError(
                        f"Description column {desc_col!r} not found in CSV columns: "
                        f"{list(peek_df.columns)}"
                    )

                for chunk in reader:
                    chunk_success = 0
                    chunk_failed = 0
                    chunk_review = 0

                    for _idx, row in chunk.iterrows():
                        description_raw = row.get(desc_col)
                        description = (
                            str(description_raw)
                            if not pd.isna(description_raw)
                            else ""
                        )

                        ticket_id: str | None = None
                        if ticket_id_col is not None and ticket_id_col in row.index:
                            raw = row[ticket_id_col]
                            ticket_id = str(raw) if not pd.isna(raw) else None

                        try:
                            result = await self._classification_service.classify_text(
                                description=description,
                                ticket_id=ticket_id,
                                batch_id=batch_id,
                            )

                            output_row = self._result_to_row(result)
                            self._exporter.append_row(batch_id, output_row)
                            chunk_success += 1
                            if result.review_required:
                                chunk_review += 1

                        except Exception as exc:
                            # Per-row error isolation — record and continue
                            logger.warning(
                                "Row error in batch %s: %s — %s",
                                batch_id,
                                type(exc).__name__,
                                exc,
                            )
                            error_row = self._error_row(
                                ticket_id=str(ticket_id) if ticket_id else "",
                                error=f"{type(exc).__name__}: {exc}",
                            )
                            self._exporter.append_row(batch_id, error_row)
                            chunk_failed += 1

                    total_success += chunk_success
                    total_failed += chunk_failed
                    total_review += chunk_review

                    # Update progress after each chunk
                    batch_repo.increment_progress(
                        batch_id,
                        success_delta=chunk_success,
                        failed_delta=chunk_failed,
                        review_required_delta=chunk_review,
                    )

            except Exception as exc:
                catastrophic_error = f"{type(exc).__name__}: {exc}"
                logger.exception("Catastrophic failure in batch %s", batch_id)

            # 7. Finalise output file
            self._exporter.finalize(batch_id)

            # 8. Set final status
            if catastrophic_error is not None:
                batch_repo.mark_failed(batch_id, catastrophic_error)
            elif total_failed > 0:
                batch_repo.mark_partial_failed(
                    batch_id,
                    str(output_path),
                    error_message=(
                        f"{total_failed}/{total_rows} rows failed"
                    ),
                )
            else:
                batch_repo.mark_completed(batch_id, str(output_path))

    # ------------------------------------------------------------------ row builders

    @staticmethod
    def _result_to_row(result: object) -> dict[str, object]:
        """Convert a :class:`ClassificationResult` into a flat CSV row dict.

        Compound fields (lists / enums) are left as Python objects; the exporter
        will serialise them to JSON strings.
        """
        primary = result.primary_category  # type: ignore[attr-defined]
        return {
            "ticket_id": result.ticket_id or "",  # type: ignore[attr-defined]
            "primary_category": primary.value if hasattr(primary, "value") else str(primary),
            "secondary_categories": [
                c.value if hasattr(c, "value") else str(c)
                for c in (result.secondary_categories or [])  # type: ignore[attr-defined]
            ],
            "confidence": result.confidence,  # type: ignore[attr-defined]
            "review_required": result.review_required,  # type: ignore[attr-defined]
            "review_reasons": result.review_reasons or [],  # type: ignore[attr-defined]
            "key_symptoms": result.key_symptoms or [],  # type: ignore[attr-defined]
            "summary": result.summary or "",  # type: ignore[attr-defined]
            "troubleshooting_steps": result.troubleshooting_steps or [],  # type: ignore[attr-defined]
            "llm_model": result.llm_model or "",  # type: ignore[attr-defined]
            "llm_latency_ms": (
                result.llm_latency_ms if result.llm_latency_ms is not None else ""  # type: ignore[attr-defined]
            ),
            "processed_at": datetime.now(UTC).isoformat(),
            "error": result.error or "",  # type: ignore[attr-defined]
        }

    @staticmethod
    def _error_row(ticket_id: str, error: str) -> dict[str, object]:
        """Build a row representing a processing error."""
        return {
            "ticket_id": ticket_id,
            "primary_category": "",
            "secondary_categories": [],
            "confidence": 0.0,
            "review_required": True,
            "review_reasons": ["REVIEW_ROW_ERROR"],
            "key_symptoms": [],
            "summary": "",
            "troubleshooting_steps": [],
            "llm_model": "",
            "llm_latency_ms": "",
            "processed_at": datetime.now(UTC).isoformat(),
            "error": error,
        }
