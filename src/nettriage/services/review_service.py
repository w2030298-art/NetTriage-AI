"""Review update service — Module G Step 32."""

from __future__ import annotations

from datetime import UTC, datetime

from nettriage.api.errors import APIError, APIErrorCode
from nettriage.repositories.ticket_repository import TicketRepository
from nettriage.schemas.ticket import ReviewUpdateRequest, ReviewUpdateResponse


class ReviewService:
    """Handle human review updates for classified tickets."""

    def __init__(self, ticket_repository: TicketRepository) -> None:
        self._repo = ticket_repository

    def update_review(
        self,
        record_id: int,
        request: ReviewUpdateRequest,
    ) -> ReviewUpdateResponse:
        """Update the review status and optional category for a ticket.

        Raises:
            APIError(code=TICKET_NOT_FOUND): If no record exists with *record_id*.
        """
        record = self._repo.get_by_id(record_id)
        if record is None:
            raise APIError(
                code=APIErrorCode.TICKET_NOT_FOUND,
                message=f"Ticket record {record_id} not found",
            )

        updated = self._repo.update_review_status(
            record_id=record_id,
            review_status=request.review_status.value,
            reviewed_category=(
                request.reviewed_category.value
                if request.reviewed_category is not None
                else None
            ),
            review_note=request.review_note,
        )

        return ReviewUpdateResponse(
            record_id=updated.id or record_id,
            review_status=request.review_status,
            reviewed_category=request.reviewed_category,
            review_note=request.review_note,
            updated_at=datetime.now(UTC),
        )
