"""Typed API error codes and exception for NetTriage AI."""

from enum import StrEnum
from typing import Any


class APIErrorCode(StrEnum):
    """Machine-readable error codes returned in every error response."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    CSV_FILE_TOO_LARGE = "CSV_FILE_TOO_LARGE"
    CSV_DESCRIPTION_COLUMN_MISSING = "CSV_DESCRIPTION_COLUMN_MISSING"
    CSV_ROW_LIMIT_EXCEEDED = "CSV_ROW_LIMIT_EXCEEDED"
    BATCH_NOT_FOUND = "BATCH_NOT_FOUND"
    TICKET_NOT_FOUND = "TICKET_NOT_FOUND"
    LLM_TEMPORARILY_UNAVAILABLE = "LLM_TEMPORARILY_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class APIError(Exception):
    """Application-level exception with a structured error response payload."""

    def __init__(
        self,
        code: APIErrorCode,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
