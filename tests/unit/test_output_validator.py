"""Unit tests for ClassificationOutputValidator — Module F Step 29."""

from __future__ import annotations

import pytest

from nettriage.llm.errors import LLMOutputParseError, LLMOutputValidationError
from nettriage.llm.output_validator import ClassificationOutputValidator


class TestParseAndValidate:
    """Tests for ClassificationOutputValidator.parse_and_validate."""

    def test_valid_json_passes(self) -> None:
        """A well-formed JSON string produces a valid LLMClassificationOutput."""
        raw = (
            '{"primary_category":"HIGH_LATENCY",'
            '"secondary_categories":["DNS_FAILURE"],'
            '"confidence":0.82,'
            '"category_scores":{"HIGH_LATENCY":0.82,"DNS_FAILURE":0.55},'
            '"key_symptoms":["high ping times"],'
            '"summary":"High latency issue.",'
            '"troubleshooting_steps":["Step 1","Step 2"]}'
        )
        result = ClassificationOutputValidator.parse_and_validate(raw)

        assert result.primary_category.value == "HIGH_LATENCY"
        assert result.secondary_categories[0].value == "DNS_FAILURE"
        assert result.confidence == 0.82
        assert result.key_symptoms == ["high ping times"]
        assert result.summary == "High latency issue."
        assert len(result.troubleshooting_steps) == 2

    def test_invalid_json_raises_parse_error(self) -> None:
        """Malformed JSON triggers LLMOutputParseError."""
        with pytest.raises(LLMOutputParseError, match="Failed to parse"):
            ClassificationOutputValidator.parse_and_validate("{not valid")

    def test_empty_string_raises_parse_error(self) -> None:
        """Empty content triggers LLMOutputParseError."""
        with pytest.raises(LLMOutputParseError, match="empty"):
            ClassificationOutputValidator.parse_and_validate("")

    def test_whitespace_only_raises_parse_error(self) -> None:
        """Whitespace-only content triggers LLMOutputParseError."""
        with pytest.raises(LLMOutputParseError, match="empty"):
            ClassificationOutputValidator.parse_and_validate("   \n\t  ")

    def test_non_object_raises_parse_error(self) -> None:
        """A JSON array instead of object triggers LLMOutputParseError."""
        with pytest.raises(LLMOutputParseError, match="not a JSON object"):
            ClassificationOutputValidator.parse_and_validate("[1, 2, 3]")

    def test_missing_required_field_raises_validation_error(self) -> None:
        """Missing primary_category triggers LLMOutputValidationError."""
        raw = (
            '{"secondary_categories":[],'
            '"confidence":0.5,'
            '"category_scores":{},'
            '"key_symptoms":[],'
            '"summary":"missing primary",'
            '"troubleshooting_steps":["do something"]}'
        )
        with pytest.raises(LLMOutputValidationError, match="failed schema validation"):
            ClassificationOutputValidator.parse_and_validate(raw)

    def test_non_enum_category_scores_key_raises(self) -> None:
        """A category_scores key not in FaultCategory raises LLMOutputValidationError."""
        raw = (
            '{"primary_category":"UNKNOWN",'
            '"secondary_categories":[],'
            '"confidence":0.5,'
            '"category_scores":{"NOT_A_VALID_CATEGORY":0.9},'
            '"key_symptoms":[],'
            '"summary":"test",'
            '"troubleshooting_steps":["step"]}'
        )
        with pytest.raises(LLMOutputValidationError, match="NOT_A_VALID_CATEGORY"):
            ClassificationOutputValidator.parse_and_validate(raw)

    def test_invalid_confidence_out_of_range_raises(self) -> None:
        """Confidence > 1.0 triggers LLMOutputValidationError."""
        raw = (
            '{"primary_category":"UNKNOWN",'
            '"secondary_categories":[],'
            '"confidence":9.99,'
            '"category_scores":{},'
            '"key_symptoms":[],'
            '"summary":"test",'
            '"troubleshooting_steps":["step"]}'
        )
        with pytest.raises(LLMOutputValidationError, match="failed schema validation"):
            ClassificationOutputValidator.parse_and_validate(raw)

    def test_zero_troubleshooting_steps_raises(self) -> None:
        """Empty troubleshooting_steps triggers LLMOutputValidationError."""
        raw = (
            '{"primary_category":"UNKNOWN",'
            '"secondary_categories":[],'
            '"confidence":0.5,'
            '"category_scores":{},'
            '"key_symptoms":[],'
            '"summary":"test",'
            '"troubleshooting_steps":[]}'
        )
        with pytest.raises(LLMOutputValidationError, match="failed schema validation"):
            ClassificationOutputValidator.parse_and_validate(raw)
