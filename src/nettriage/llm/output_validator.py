"""Validates raw LLM JSON output against the Pydantic schema — Module F Step 28."""

from __future__ import annotations

import json
import logging

from pydantic import ValidationError

from nettriage.llm.errors import LLMOutputParseError, LLMOutputValidationError
from nettriage.schemas.classification import LLMClassificationOutput
from nettriage.schemas.enums import FaultCategory

logger = logging.getLogger(__name__)


class ClassificationOutputValidator:
    """Parse and validate raw LLM JSON strings into ``LLMClassificationOutput``."""

    @staticmethod
    def parse_and_validate(raw_content: str) -> LLMClassificationOutput:
        """Parse a raw JSON string and validate against the output schema.

        Args:
            raw_content: The raw text returned by an LLM provider.

        Returns:
            A validated ``LLMClassificationOutput`` instance.

        Raises:
            LLMOutputParseError: If ``raw_content`` is empty or not valid JSON.
            LLMOutputValidationError: If the JSON fails Pydantic validation,
                including when ``category_scores`` keys are not valid
                ``FaultCategory`` values.
        """
        stripped = raw_content.strip()

        if not stripped:
            raise LLMOutputParseError("Received empty response content")

        try:
            data: object = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise LLMOutputParseError(
                f"Failed to parse LLM output as JSON: {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise LLMOutputParseError(
                f"LLM output is not a JSON object (got {type(data).__name__})"
            )

        # Pre-validate category_scores keys against FaultCategory enum
        category_scores = data.get("category_scores")
        if isinstance(category_scores, dict):
            valid_keys = {m.value for m in FaultCategory}
            for key in category_scores:
                if key not in valid_keys:
                    raise LLMOutputValidationError(
                        f"'category_scores' key '{key}' is not a valid "
                        f"FaultCategory value"
                    )

        try:
            return LLMClassificationOutput.model_validate(data)
        except ValidationError as exc:
            raise LLMOutputValidationError(
                f"LLM output failed schema validation: {exc}"
            ) from exc
