"""Unit tests for ClassificationService — Module G Step 34.

Uses FakeLLMClient exclusively — NEVER calls real DeepSeek API.
"""

from __future__ import annotations

import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from nettriage.core.config import Settings
from nettriage.llm.output_validator import ClassificationOutputValidator
from nettriage.repositories.ticket_repository import TicketRepository
from nettriage.rules.keyword_rules import KEYWORD_RULES
from nettriage.rules.review_policy import ReviewPolicy
from nettriage.rules.rule_classifier import RuleBasedClassifier
from nettriage.schemas.enums import FaultCategory
from tests.fakes import FakeLLMClient

# ------------------------------------------------------------------ fixtures


@pytest.fixture
def in_memory_session():
    """Yields a SQLModel Session backed by an in-memory SQLite database."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def settings():
    """Return a Settings instance with test defaults."""
    return Settings()


@pytest.fixture
def ticket_repo(in_memory_session: Session) -> TicketRepository:
    """Return a TicketRepository backed by in-memory SQLite."""
    return TicketRepository(in_memory_session)


@pytest.fixture
def validator() -> ClassificationOutputValidator:
    """Return a real ClassificationOutputValidator."""
    return ClassificationOutputValidator()


@pytest.fixture
def rule_classifier() -> RuleBasedClassifier:
    """Return a RuleBasedClassifier with real keyword rules."""
    return RuleBasedClassifier(dict(KEYWORD_RULES))


@pytest.fixture
def review_policy() -> ReviewPolicy:
    """Return a ReviewPolicy with default thresholds."""
    return ReviewPolicy(confidence_threshold=0.80, conflict_score_delta=0.08)


def _make_service(
    llm: FakeLLMClient,
    ticket_repo: TicketRepository,
    validator: ClassificationOutputValidator,
    rule_classifier: RuleBasedClassifier,
    review_policy: ReviewPolicy,
    settings: Settings,
):
    """Helper to construct ClassificationService (avoids import-time circular issues)."""
    from nettriage.services.classification_service import ClassificationService

    return ClassificationService(
        llm_client=llm,  # type: ignore[arg-type]
        validator=validator,
        rule_classifier=rule_classifier,
        review_policy=review_policy,
        ticket_repository=ticket_repo,
        settings=settings,
    )


# ------------------------------------------------------------------ test data

LONG_DESCRIPTION = (
    "The network connection has been experiencing high latency since 8am this morning. "
    "Response times exceed 500ms when they should be under 20ms. "
    "Traceroute reveals delays at intermediate hops. "
    "All services are slow but no authentication errors are reported."
)


# ------------------------------------------------------------------ tests


@pytest.mark.asyncio
async def test_llm_success_high_confidence(
    ticket_repo, validator, rule_classifier, review_policy, settings
):
    """LLM returns valid JSON with high confidence → no review required."""
    fake = FakeLLMClient(
        response_mode="success",
        custom_content={
            "primary_category": "HIGH_LATENCY",
            "secondary_categories": ["BANDWIDTH_DEGRADATION"],
            "confidence": 0.92,
            "category_scores": {"HIGH_LATENCY": 0.92, "BANDWIDTH_DEGRADATION": 0.55},
            "key_symptoms": ["latency spikes"],
            "summary": "High latency issue on network.",
            "troubleshooting_steps": ["Check route", "Measure latency"],
        },
    )
    svc = _make_service(fake, ticket_repo, validator, rule_classifier, review_policy, settings)

    result = await svc.classify_text(LONG_DESCRIPTION, ticket_id="TKT-001")

    assert result.primary_category == FaultCategory.HIGH_LATENCY
    assert result.confidence == 0.92
    assert result.review_required is False
    assert result.review_reasons == []
    assert result.fallback_used is False
    assert result.error is None
    assert result.llm_raw_output is not None
    assert result.ticket_id == "TKT-001"


@pytest.mark.asyncio
async def test_llm_success_low_confidence_review(
    ticket_repo, validator, rule_classifier, review_policy, settings
):
    """LLM confidence below threshold → review_required=True."""
    fake = FakeLLMClient(
        response_mode="success",
        custom_content={
            "primary_category": "DNS_FAILURE",
            "secondary_categories": [],
            "confidence": 0.65,
            "category_scores": {"DNS_FAILURE": 0.65, "PACKET_LOSS": 0.55},
            "key_symptoms": ["dns lookup failure"],
            "summary": "DNS issues.",
            "troubleshooting_steps": ["Check DNS config"],
        },
    )
    svc = _make_service(fake, ticket_repo, validator, rule_classifier, review_policy, settings)

    result = await svc.classify_text("DNS resolution failing repeatedly for all users")

    assert result.review_required is True
    assert "REVIEW_LOW_CONFIDENCE" in result.review_reasons


@pytest.mark.asyncio
async def test_llm_vs_rule_conflict(
    ticket_repo, validator, review_policy, settings
):
    """Rule strong match disagrees with LLM → review_required."""
    # LLM says DNS_FAILURE, but rule says HIGH_LATENCY (description matches latency keywords)
    fake = FakeLLMClient(
        response_mode="success",
        custom_content={
            "primary_category": "DNS_FAILURE",
            "secondary_categories": [],
            "confidence": 0.88,
            "category_scores": {"DNS_FAILURE": 0.88, "HIGH_LATENCY": 0.30},
            "key_symptoms": ["dns lookup"],
            "summary": "DNS failure.",
            "troubleshooting_steps": ["Check DNS"],
        },
    )
    rc = RuleBasedClassifier(dict(KEYWORD_RULES))
    svc = _make_service(fake, ticket_repo, validator, rc, review_policy, settings)

    # This text has keywords that match HIGH_LATENCY strongly
    result = await svc.classify_text("延迟高 延迟高 延迟高 时延高")

    # Rule should strongly match HIGH_LATENCY → conflict with LLM's DNS_FAILURE
    assert result.review_required is True
    assert "REVIEW_RULE_LLM_CONFLICT" in result.review_reasons


@pytest.mark.asyncio
async def test_llm_invalid_json_fallback_to_rules(
    ticket_repo, validator, rule_classifier, review_policy, settings
):
    """LLM returns invalid JSON → tries repair fails → falls back to rules."""
    fake = FakeLLMClient(response_mode="invalid_json")
    svc = _make_service(fake, ticket_repo, validator, rule_classifier, review_policy, settings)

    result = await svc.classify_text("packet loss and high latency everywhere")

    assert result.fallback_used is True
    assert result.review_required is True
    assert "REVIEW_FALLBACK_USED" in result.review_reasons
    assert "REVIEW_LLM_RESULT_MISSING" in result.review_reasons


@pytest.mark.asyncio
async def test_llm_provider_error_fallback(
    ticket_repo, validator, rule_classifier, review_policy, settings
):
    """LLM provider error → fallback to rule-only classification."""
    fake = FakeLLMClient(response_mode="provider_error")
    svc = _make_service(fake, ticket_repo, validator, rule_classifier, review_policy, settings)

    result = await svc.classify_text("packet loss and high latency everywhere")

    assert result.fallback_used is True
    assert result.review_required is True
    assert "Simulated provider error" in (result.error or "")


@pytest.mark.asyncio
async def test_llm_empty_response_fallback(
    ticket_repo, validator, rule_classifier, review_policy, settings
):
    """LLM empty response → fallback to rules."""
    fake = FakeLLMClient(response_mode="empty_content")
    svc = _make_service(fake, ticket_repo, validator, rule_classifier, review_policy, settings)

    result = await svc.classify_text("packet loss and high latency everywhere")

    assert result.fallback_used is True
    assert result.review_required is True


@pytest.mark.asyncio
async def test_insufficient_description_unknown_review(
    ticket_repo, validator, rule_classifier, review_policy, settings
):
    """Very short text → UNKNOWN result with review_required=True."""
    fake = FakeLLMClient(response_mode="success")  # won't be called
    svc = _make_service(fake, ticket_repo, validator, rule_classifier, review_policy, settings)

    result = await svc.classify_text("help")

    assert result.primary_category == FaultCategory.UNKNOWN
    assert result.review_required is True
    assert result.fallback_used is True
    assert "REVIEW_INSUFFICIENT_CONTENT" in result.review_reasons
    assert result.confidence == 0.0


@pytest.mark.asyncio
async def test_repository_called_and_saves_result(
    ticket_repo, validator, rule_classifier, review_policy, settings
):
    """Verify that classification result is persisted via TicketRepository."""
    fake = FakeLLMClient(response_mode="success")
    svc = _make_service(fake, ticket_repo, validator, rule_classifier, review_policy, settings)

    await svc.classify_text(LONG_DESCRIPTION, ticket_id="TKT-SAVE", source="csv", batch_id="B001")

    # Query back from DB
    from nettriage.schemas.ticket import TicketQueryFilters, TicketRecordResponse

    filters = TicketQueryFilters(limit=10)
    records = ticket_repo.list_results(filters)

    assert len(records) == 1
    rec = records[0]
    resp = TicketRecordResponse.model_validate(rec)
    assert resp.ticket_id == "TKT-SAVE"
    assert resp.source == "csv"
    assert resp.batch_id == "B001"
    assert resp.primary_category == "HIGH_LATENCY"
    assert resp.fallback_used is False
