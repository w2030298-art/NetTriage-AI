"""Classification service orchestrating LLM, rules, and review — Module G Steps 30-31.

Primary flow (Step 30):
  1. Normalize → check insufficient → UNKNOWN early exit
  2. LLM classify → validate → rule classify → review policy → build result → save DB

Fallback flow (Step 31):
  - JSON parse error → strip markdown fences, retry
  - LLM error → fallback to rule-only classification
  - All fallback results have fallback_used=True, review_required=True
"""

from __future__ import annotations

import hashlib
import json
import logging
import re

from nettriage.core.config import Settings
from nettriage.llm.base import LLMClient, LLMRawResponse
from nettriage.llm.errors import LLMError, LLMOutputParseError, LLMOutputValidationError
from nettriage.llm.output_validator import ClassificationOutputValidator
from nettriage.repositories.ticket_repository import TicketRecordCreate, TicketRepository
from nettriage.rules.review_policy import ReviewPolicy
from nettriage.rules.rule_classifier import RuleBasedClassifier, RuleClassificationResult
from nettriage.rules.text_normalizer import TextNormalizer
from nettriage.schemas.classification import ClassificationResult, LLMClassificationOutput
from nettriage.schemas.enums import FaultCategory, ReviewStatus

logger = logging.getLogger(__name__)

_MARKDOWN_FENCE_RE = re.compile(
    r"^```(?:json)?\s*\n?(.*?)\n?```$", re.DOTALL | re.IGNORECASE
)


class ClassificationService:
    """Orchestrate fault classification with LLM + rule fallback."""

    def __init__(
        self,
        llm_client: LLMClient,
        validator: ClassificationOutputValidator,
        rule_classifier: RuleBasedClassifier,
        review_policy: ReviewPolicy,
        ticket_repository: TicketRepository,
        settings: Settings,
    ) -> None:
        self._llm = llm_client
        self._validator = validator
        self._rule_classifier = rule_classifier
        self._review_policy = review_policy
        self._ticket_repo = ticket_repository
        self._settings = settings
        self._normalizer = TextNormalizer()

    # ------------------------------------------------------------------ public API

    async def classify_text(
        self,
        description: str,
        ticket_id: str | None = None,
        source: str | None = None,
        customer_region: str | None = None,
        batch_id: str | None = None,
    ) -> ClassificationResult:
        """Classify a single fault description.

        Args:
            description: The free-text fault description.
            ticket_id: Optional external ticket identifier.
            source: Optional data source label.
            customer_region: Optional customer region.
            batch_id: Optional batch processing identifier.

        Returns:
            A ``ClassificationResult`` with all classification + review metadata.
        """
        # 1. Normalize text
        normalized = TextNormalizer.normalize(description)

        # 2. Insufficient content → early exit
        if TextNormalizer.is_insufficient(normalized):
            return self._build_insufficient_result(
                description=description,
                normalized=normalized,
                ticket_id=ticket_id,
                source=source,
                customer_region=customer_region,
                batch_id=batch_id,
            )

        # 3. Run rule classifier first (needed for either path)
        rule_result = self._rule_classifier.classify(normalized)

        # 4. Try LLM classification with fallback on failure
        try:
            llm_result, raw_response = await self._classify_with_llm(normalized)
            parse_error: str | None = None
            fallback_used = False
        except (LLMOutputParseError, LLMOutputValidationError) as exc:
            logger.warning(
                "LLM parse/validation error, trying repair — %s", exc
            )
            try:
                llm_result, raw_response = await self._classify_with_llm_repair(normalized)
                parse_error = None
                fallback_used = False
            except (LLMOutputParseError, LLMOutputValidationError) as repair_exc:
                logger.warning("LLM repair also failed, falling back to rules — %s", repair_exc)
                return self._build_fallback_result(
                    description=description,
                    normalized=normalized,
                    rule_result=rule_result,
                    ticket_id=ticket_id,
                    source=source,
                    customer_region=customer_region,
                    batch_id=batch_id,
                    error=f"{type(repair_exc).__name__}: failed to parse LLM output",
                )
        except LLMError as exc:
            logger.warning("LLM provider error, falling back to rules — %s", exc)
            return self._build_fallback_result(
                description=description,
                normalized=normalized,
                rule_result=rule_result,
                ticket_id=ticket_id,
                source=source,
                customer_region=customer_region,
                batch_id=batch_id,
                error=f"{type(exc).__name__}: {exc}",
            )

        # 5. Evaluate review policy
        review_decision = self._review_policy.evaluate(
            llm_result=llm_result,
            rule_result=rule_result,
            parse_error=parse_error,
            fallback_used=fallback_used,
        )

        # 6. Build result DTO
        desc_hash = hashlib.sha256(description.encode("utf-8")).hexdigest()

        result = ClassificationResult(
            primary_category=llm_result.primary_category,
            secondary_categories=llm_result.secondary_categories,
            confidence=llm_result.confidence,
            category_scores=llm_result.category_scores,
            key_symptoms=llm_result.key_symptoms,
            summary=llm_result.summary,
            troubleshooting_steps=llm_result.troubleshooting_steps,
            review_required=review_decision.review_required,
            review_reasons=review_decision.reasons,
            llm_model=raw_response.model,
            llm_raw_output=raw_response.content,
            llm_latency_ms=float(raw_response.latency_ms),
            fallback_used=fallback_used,
            error=None,
            ticket_id=ticket_id,
            batch_id=batch_id,
            source=source,
            customer_region=customer_region,
        )

        # 7. Persist to database
        self._persist_result(result, desc_hash, description, raw_response)

        return result

    # ------------------------------------------------------------------ LLM helpers

    async def _classify_with_llm(
        self, description: str
    ) -> tuple[LLMClassificationOutput, LLMRawResponse]:
        """Call LLM, parse, and validate in one step.  Raises on failure."""
        raw_response = await self._llm.classify_fault(description)
        llm_output = self._validator.parse_and_validate(raw_response.content)
        return llm_output, raw_response

    async def _classify_with_llm_repair(
        self, description: str
    ) -> tuple[LLMClassificationOutput, LLMRawResponse]:
        """Call LLM, attempt JSON repair (strip markdown fences), parse+validate."""
        raw_response = await self._llm.classify_fault(description)
        content = raw_response.content

        # Try direct parse/validate first
        try:
            return self._validator.parse_and_validate(content), raw_response
        except (LLMOutputParseError, LLMOutputValidationError):
            pass

        # Strip markdown fences and retry
        repaired = self._strip_markdown_fences(content)
        if repaired != content:
            logger.debug("Stripped markdown fences from LLM output")
            return self._validator.parse_and_validate(repaired), raw_response

        raise  # re-raise original error if repair had no effect

    # ------------------------------------------------------------------ fallback builders

    def _build_insufficient_result(
        self,
        *,
        description: str,
        normalized: str,
        ticket_id: str | None,
        source: str | None,
        customer_region: str | None,
        batch_id: str | None,
    ) -> ClassificationResult:
        """Build a result for insufficient text content."""
        desc_hash = hashlib.sha256(description.encode("utf-8")).hexdigest()

        result = ClassificationResult(
            primary_category=FaultCategory.UNKNOWN,
            secondary_categories=[],
            confidence=0.0,
            category_scores={},
            key_symptoms=[],
            summary=f"Insufficient content: {normalized[:100]}",
            troubleshooting_steps=["Provide more detailed fault description"],
            review_required=True,
            review_reasons=["REVIEW_INSUFFICIENT_CONTENT"],
            llm_raw_output=None,
            llm_latency_ms=None,
            fallback_used=True,
            error="Insufficient text: content too short for classification",
            ticket_id=ticket_id,
            batch_id=batch_id,
            source=source,
            customer_region=customer_region,
        )

        self._persist_result(result, desc_hash, description, None)
        return result

    def _build_fallback_result(
        self,
        *,
        description: str,
        normalized: str,
        rule_result: RuleClassificationResult,
        ticket_id: str | None,
        source: str | None,
        customer_region: str | None,
        batch_id: str | None,
        error: str,
    ) -> ClassificationResult:
        """Build a fallback result from rule-only classification.

        Note:
            *error* must contain only error type + summary — never a full stack trace.
        """
        desc_hash = hashlib.sha256(description.encode("utf-8")).hexdigest()

        # Derive confidence from rule strength
        if rule_result.primary_category == FaultCategory.UNKNOWN:
            confidence = 0.0
        elif rule_result.strong_match:
            confidence = 0.85
        else:
            confidence = 0.50

        rule_scores: dict[str, float] = {
            k.value: v for k, v in rule_result.scores.items()
        }

        result = ClassificationResult(
            primary_category=rule_result.primary_category,
            secondary_categories=[],
            confidence=confidence,
            category_scores=rule_scores,
            key_symptoms=[],
            summary=normalized[:200],
            troubleshooting_steps=["Manual review required — LLM unavailable"],
            review_required=True,
            review_reasons=["REVIEW_FALLBACK_USED", "REVIEW_LLM_RESULT_MISSING"],
            llm_raw_output=None,
            llm_latency_ms=None,
            fallback_used=True,
            error=error,
            ticket_id=ticket_id,
            batch_id=batch_id,
            source=source,
            customer_region=customer_region,
        )

        self._persist_result(result, desc_hash, description, None)
        return result

    # ------------------------------------------------------------------ persistence

    def _persist_result(
        self,
        result: ClassificationResult,
        desc_hash: str,
        description: str,
        raw_response: LLMRawResponse | None,
    ) -> None:
        """Save the classification result to the database."""
        review_status = (
            ReviewStatus.PENDING.value
            if result.review_required
            else ReviewStatus.CONFIRMED.value
        )

        ticket_id = result.ticket_id or desc_hash[:12]

        data = TicketRecordCreate(
            ticket_id=ticket_id,
            batch_id=result.batch_id,
            description_hash=desc_hash,
            description_text=description,
            primary_category=result.primary_category.value,
            secondary_categories_json=json.dumps(
                [c.value for c in result.secondary_categories]
            ),
            confidence=result.confidence,
            category_scores_json=json.dumps(result.category_scores),
            key_symptoms_json=json.dumps(result.key_symptoms),
            summary=result.summary,
            troubleshooting_steps_json=json.dumps(result.troubleshooting_steps),
            review_required=result.review_required,
            review_status=review_status,
            review_reasons_json=json.dumps(result.review_reasons),
            llm_model=raw_response.model if raw_response else None,
            llm_raw_output=result.llm_raw_output,
            llm_latency_ms=(
                int(result.llm_latency_ms)
                if result.llm_latency_ms is not None
                else None
            ),
            fallback_used=result.fallback_used,
            error=result.error,
            source=result.source,
            customer_region=result.customer_region,
        )

        self._ticket_repo.create_result(data)

    # ------------------------------------------------------------------ JSON repair

    @staticmethod
    def _strip_markdown_fences(content: str) -> str:
        """Strip surrounding markdown code-fence markers (```json ... ```) from *content*."""
        stripped = content.strip()
        match = _MARKDOWN_FENCE_RE.match(stripped)
        if match:
            return match.group(1).strip()
        return stripped
