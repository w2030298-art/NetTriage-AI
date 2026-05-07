"""Step 40: Classify API — single fault description classification endpoint."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from nettriage.api.dependencies import get_classification_service
from nettriage.schemas.classification import ClassifyRequest, ClassifyResponse
from nettriage.services.classification_service import ClassificationService

router = APIRouter(prefix="/api/v1", tags=["classification"])


@router.post("/classify", response_model=ClassifyResponse)
async def classify_fault(
    request: ClassifyRequest,
    service: ClassificationService = Depends(get_classification_service),  # noqa: B008
) -> ClassifyResponse:
    """Classify a single fault description using LLM + rule-based fallback.

    Returns a fully populated :class:`ClassifyResponse` with the category,
    confidence, review status, and troubleshooting steps.
    """
    result = await service.classify_text(
        description=request.description,
        ticket_id=request.ticket_id,
        source=request.source,
        customer_region=request.customer_region,
    )

    return ClassifyResponse(
        **result.model_dump(),
        record_id=0,
        processed_at=datetime.now(UTC).isoformat(),
    )
