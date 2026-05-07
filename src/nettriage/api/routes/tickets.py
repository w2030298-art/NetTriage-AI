"""Step 42: Tickets API — list, detail, and review endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from nettriage.api.dependencies import get_review_service, get_ticket_service
from nettriage.schemas.enums import FaultCategory
from nettriage.schemas.ticket import (
    ReviewUpdateRequest,
    ReviewUpdateResponse,
    TicketQueryFilters,
    TicketRecordResponse,
)
from nettriage.services.review_service import ReviewService
from nettriage.services.ticket_service import TicketService

router = APIRouter(prefix="/api/v1", tags=["tickets"])


@router.get("/tickets", response_model=list[TicketRecordResponse])
async def list_tickets(
    primary_category: Annotated[
        FaultCategory | None, Query(description="Filter by primary fault category")
    ] = None,
    review_required: Annotated[
        bool | None, Query(description="Filter by review requirement")
    ] = None,
    batch_id: Annotated[
        str | None, Query(description="Filter by batch identifier")
    ] = None,
    keyword: Annotated[
        str | None, Query(description="Search keyword in description/summary")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=1000, description="Results per page")] = 50,
    offset: Annotated[int, Query(ge=0, description="Pagination offset")] = 0,
    service: TicketService = Depends(get_ticket_service),  # noqa: B008
) -> list[TicketRecordResponse]:
    """List ticket classification records with optional filters."""
    filters = TicketQueryFilters(
        primary_category=primary_category,
        review_required=review_required,
        batch_id=batch_id,
        keyword=keyword,
        limit=limit,
        offset=offset,
    )
    return service.list_tickets(filters)


@router.get("/tickets/{record_id}", response_model=TicketRecordResponse)
async def get_ticket(
    record_id: int,
    service: TicketService = Depends(get_ticket_service),  # noqa: B008
) -> TicketRecordResponse:
    """Retrieve a single ticket classification record by its database ID."""
    return service.get_ticket(record_id)


@router.patch("/tickets/{record_id}/review", response_model=ReviewUpdateResponse)
async def update_review(
    record_id: int,
    review: ReviewUpdateRequest,
    service: ReviewService = Depends(get_review_service),  # noqa: B008
) -> ReviewUpdateResponse:
    """Update the review status and optionally correct the category for a ticket."""
    return service.update_review(record_id, review)
