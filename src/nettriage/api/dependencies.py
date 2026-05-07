"""FastAPI dependency injection wiring — Module G Step 33.

All dependency factory functions follow the FastAPI ``Depends`` pattern,
allowing test overrides via ``app.dependency_overrides``.
"""

from __future__ import annotations

import functools
from collections.abc import Generator

from fastapi import Depends
from sqlalchemy import Engine
from sqlmodel import Session

from nettriage.batch.file_store import BatchFileStore
from nettriage.core.config import Settings, get_settings
from nettriage.db.session import create_engine_from_settings, get_session
from nettriage.llm.base import LLMClient
from nettriage.llm.deepseek import DeepSeekClient
from nettriage.llm.output_validator import ClassificationOutputValidator
from nettriage.repositories.batch_repository import BatchRepository
from nettriage.repositories.ticket_repository import TicketRepository
from nettriage.rules.keyword_rules import KEYWORD_RULES
from nettriage.rules.review_policy import ReviewPolicy
from nettriage.rules.rule_classifier import RuleBasedClassifier
from nettriage.rules.text_normalizer import TextNormalizer
from nettriage.services.batch_service import BatchService
from nettriage.services.classification_service import ClassificationService
from nettriage.services.review_service import ReviewService
from nettriage.services.ticket_service import TicketService

# ------------------------------------------------------------------ engine (module-level singleton)


@functools.lru_cache(maxsize=1)
def _get_engine() -> Engine:
    """Lazily create and cache the SQLAlchemy engine from settings."""
    settings = get_settings()
    return create_engine_from_settings(settings)


# ------------------------------------------------------------------ core dependencies


def get_settings_dep() -> Settings:
    """Return the cached application Settings singleton."""
    return get_settings()


def get_db_session() -> Generator[Session, None, None]:
    """Yield a per-request SQLAlchemy Session."""
    engine = _get_engine()
    yield from get_session(engine)


# ------------------------------------------------------------------ repositories


def get_ticket_repository(
    session: Session = Depends(get_db_session),  # noqa: B008
) -> TicketRepository:
    """Construct a TicketRepository bound to the request session."""
    return TicketRepository(session)


def get_batch_repository(
    session: Session = Depends(get_db_session),  # noqa: B008
) -> BatchRepository:
    """Construct a BatchRepository bound to the request session."""
    return BatchRepository(session)


# ------------------------------------------------------------------ LLM client

# Module-scoped mutable reference — allows tests to intercept before wiring.
# Tests should set ``app.dependency_overrides[get_llm_client] = ...`` instead.
_llm_client_override: LLMClient | None = None


def get_llm_client(
    settings: Settings = Depends(get_settings_dep),  # noqa: B008
) -> LLMClient:
    """Return the LLM client (DeepSeek by default, overridable for tests).

    Tests can replace this via ``app.dependency_overrides[get_llm_client]``.
    """
    if _llm_client_override is not None:
        return _llm_client_override
    return DeepSeekClient(settings)


# ------------------------------------------------------------------ rules / utilities


def get_text_normalizer() -> TextNormalizer:
    """Return a shared TextNormalizer instance."""
    return TextNormalizer()


def get_rule_classifier() -> RuleBasedClassifier:
    """Return a RuleBasedClassifier initialised with the default keyword rules."""
    return RuleBasedClassifier(dict(KEYWORD_RULES))


def get_review_policy(
    settings: Settings = Depends(get_settings_dep),  # noqa: B008
) -> ReviewPolicy:
    """Return a ReviewPolicy configured from application settings."""
    return ReviewPolicy(
        confidence_threshold=settings.review_confidence_threshold,
        conflict_score_delta=settings.conflict_score_delta,
    )


def get_validator() -> ClassificationOutputValidator:
    """Return a shared ClassificationOutputValidator."""
    return ClassificationOutputValidator()


# ------------------------------------------------------------------ services


def get_classification_service(
    llm_client: LLMClient = Depends(get_llm_client),  # noqa: B008
    validator: ClassificationOutputValidator = Depends(get_validator),  # noqa: B008
    rule_classifier: RuleBasedClassifier = Depends(get_rule_classifier),  # noqa: B008
    review_policy: ReviewPolicy = Depends(get_review_policy),  # noqa: B008
    ticket_repository: TicketRepository = Depends(get_ticket_repository),  # noqa: B008
    settings: Settings = Depends(get_settings_dep),  # noqa: B008
) -> ClassificationService:
    """Assemble the ClassificationService with all its collaborators."""
    return ClassificationService(
        llm_client=llm_client,
        validator=validator,
        rule_classifier=rule_classifier,
        review_policy=review_policy,
        ticket_repository=ticket_repository,
        settings=settings,
    )


def get_ticket_service(
    ticket_repo: TicketRepository = Depends(get_ticket_repository),  # noqa: B008
) -> TicketService:
    """Return a TicketService instance."""
    return TicketService(ticket_repository=ticket_repo)


def get_batch_service(
    settings: Settings = Depends(get_settings_dep),  # noqa: B008
    batch_repo: BatchRepository = Depends(get_batch_repository),  # noqa: B008
    classification_service: ClassificationService = Depends(get_classification_service),  # noqa: B008
) -> BatchService:
    """Assemble the BatchService with file store, repository, and classifier."""
    file_store = BatchFileStore(settings)
    return BatchService(
        file_store=file_store,
        batch_repository=batch_repo,
        classification_service=classification_service,
        settings=settings,
    )


def get_review_service(
    ticket_repo: TicketRepository = Depends(get_ticket_repository),  # noqa: B008
) -> ReviewService:
    """Return a ReviewService instance."""
    return ReviewService(ticket_repository=ticket_repo)
