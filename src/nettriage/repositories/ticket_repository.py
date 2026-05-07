"""TicketRecord repository — Module D Step 17."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlmodel import Session, col, or_, select

from nettriage.db.models import TicketRecord
from nettriage.schemas.ticket import TicketQueryFilters


@dataclass
class TicketRecordCreate:
    """Input data for creating a :class:`TicketRecord`."""

    ticket_id: str
    batch_id: str | None = None
    description_hash: str = ""
    description_text: str = ""
    primary_category: str = ""
    secondary_categories_json: str = "[]"
    confidence: float = 0.0
    category_scores_json: str = "{}"
    key_symptoms_json: str = "[]"
    summary: str = ""
    troubleshooting_steps_json: str = "[]"
    review_required: bool = False
    review_status: str = "PENDING"
    review_reasons_json: str = "[]"
    reviewed_category: str | None = None
    review_note: str | None = None
    llm_model: str | None = None
    llm_raw_output: str | None = None
    llm_latency_ms: int | None = None
    fallback_used: bool = False
    error: str | None = None
    source: str | None = None
    customer_region: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class TicketRepository:
    """Data-access layer for :class:`TicketRecord`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_result(self, data: TicketRecordCreate) -> TicketRecord:
        """Persist a new ticket classification record."""
        record = TicketRecord(**vars(data))
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record

    def get_by_id(self, record_id: int) -> TicketRecord | None:
        """Return the record identified by *record_id* or ``None``."""
        return self._session.get(TicketRecord, record_id)

    def list_results(self, filters: TicketQueryFilters) -> list[TicketRecord]:
        """Query ticket records using the supplied *filters*."""
        stmt = select(TicketRecord)

        if filters.primary_category is not None:
            stmt = stmt.where(col(TicketRecord.primary_category) == filters.primary_category.value)
        if filters.review_required is not None:
            stmt = stmt.where(col(TicketRecord.review_required) == filters.review_required)
        if filters.batch_id is not None:
            stmt = stmt.where(col(TicketRecord.batch_id) == filters.batch_id)
        if filters.keyword is not None:
            pattern = f"%{filters.keyword}%"
            stmt = stmt.where(
                or_(
                    col(TicketRecord.description_text).like(pattern),
                    col(TicketRecord.summary).like(pattern),
                )
            )

        stmt = stmt.offset(filters.offset).limit(filters.limit)
        results = self._session.exec(stmt).all()
        return list(results)

    def update_review_status(
        self,
        record_id: int,
        review_status: str,
        reviewed_category: str | None = None,
        review_note: str | None = None,
    ) -> TicketRecord:
        """Update the review fields on an existing record and return it."""
        record = self.get_by_id(record_id)
        if record is None:
            raise ValueError(f"TicketRecord with id={record_id} not found")

        record.review_status = review_status
        record.reviewed_category = reviewed_category
        record.review_note = review_note
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record
