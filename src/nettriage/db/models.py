"""SQLModel table definitions for NetTriage AI — Module D Step 16."""

from datetime import datetime

from sqlmodel import Field, SQLModel


class TicketRecord(SQLModel, table=True):
    """Persistent ticket classification result."""

    id: int | None = Field(default=None, primary_key=True)
    ticket_id: str = Field(index=True)
    batch_id: str | None = Field(default=None, index=True)
    description_hash: str = Field(index=True)
    description_text: str = Field()
    primary_category: str = Field(index=True)
    secondary_categories_json: str = Field(default="[]")
    confidence: float = Field(index=True)
    category_scores_json: str = Field(default="{}")
    key_symptoms_json: str = Field(default="[]")
    summary: str = Field(default="")
    troubleshooting_steps_json: str = Field(default="[]")
    review_required: bool = Field(index=True)
    review_status: str = Field(default="PENDING", index=True)
    review_reasons_json: str = Field(default="[]")
    reviewed_category: str | None = Field(default=None)
    review_note: str | None = Field(default=None)
    llm_model: str | None = Field(default=None)
    llm_raw_output: str | None = Field(default=None)
    llm_latency_ms: int | None = Field(default=None)
    fallback_used: bool = Field(default=False)
    error: str | None = Field(default=None)
    source: str | None = Field(default=None)
    customer_region: str | None = Field(default=None)
    created_at: datetime | None = Field(default=None)
    processed_at: datetime = Field(
        default_factory=datetime.utcnow,  # deprecated but per spec
        index=True,
    )


class BatchJob(SQLModel, table=True):
    """Batch processing job metadata."""

    id: int | None = Field(default=None, primary_key=True)
    batch_id: str = Field(unique=True, index=True)
    input_filename: str = Field()
    stored_input_path: str = Field()
    output_path: str | None = Field(default=None)
    status: str = Field(default="PENDING", index=True)
    total_rows: int = Field(default=0)
    processed_rows: int = Field(default=0)
    success_rows: int = Field(default=0)
    failed_rows: int = Field(default=0)
    review_required_rows: int = Field(default=0)
    error_message: str | None = Field(default=None)
    created_at: datetime = Field(
        default_factory=datetime.utcnow,  # deprecated but per spec
        index=True,
    )
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
