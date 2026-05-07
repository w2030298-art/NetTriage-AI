"""Ticket query service — Module G Step 32."""

from __future__ import annotations

from nettriage.api.errors import APIError, APIErrorCode
from nettriage.repositories.ticket_repository import TicketRepository
from nettriage.schemas.ticket import TicketQueryFilters, TicketRecordResponse


class TicketService:
    """Query and retrieve ticket classification records."""

    def __init__(self, ticket_repository: TicketRepository) -> None:
        self._repo = ticket_repository

    def list_tickets(self, filters: TicketQueryFilters) -> list[TicketRecordResponse]:
        """Return ticket records matching the supplied filters."""
        records = self._repo.list_results(filters)
        return [TicketRecordResponse.model_validate(r) for r in records]

    def get_ticket(self, record_id: int) -> TicketRecordResponse:
        """Return a single ticket record by its database ID.

        Raises:
            APIError(code=TICKET_NOT_FOUND): If no record exists with *record_id*.
        """
        record = self._repo.get_by_id(record_id)
        if record is None:
            raise APIError(
                code=APIErrorCode.TICKET_NOT_FOUND,
                message=f"Ticket record {record_id} not found",
            )
        return TicketRecordResponse.model_validate(record)
