"""Tests for CSVFieldMapper — Module H Step 36."""

from __future__ import annotations

import pytest

from nettriage.batch.field_mapper import CSVFieldMapper
from nettriage.schemas.batch import CSVFieldMapping


class TestInferMappingDescriptionAliases:
    """Verify all known description column aliases are matched (case-insensitive)."""

    @pytest.mark.parametrize(
        "col",
        [
            "description",
            "Description",
            "DESCRIPTION",
            "desc",
            "Desc",
            "content",
            "CONTENT",
            "fault_description",
            "FAULT_DESCRIPTION",
            "problem_description",
            "故障描述",
            "问题描述",
            "故障现象",
        ],
    )
    def test_description_alias_matched(self, col: str) -> None:
        mapping = CSVFieldMapper.infer_mapping([col])
        assert mapping.description_column == col

    def test_description_matched_in_mixed_columns(self) -> None:
        mapping = CSVFieldMapper.infer_mapping(
            ["timestamp", "desc", "priority", "Comment"]
        )
        assert mapping.description_column == "desc"

    def test_first_match_wins_with_multiple_aliases(self) -> None:
        """When multiple description aliases exist, the first input column match wins."""
        mapping = CSVFieldMapper.infer_mapping(
            ["content", "description"]
        )
        # Implementation picks first alias from DESCRIPTION_ALIASES order ("description")
        assert mapping.description_column == "description"


class TestMissingDescriptionColumn:
    def test_raises_value_error_on_empty_columns(self) -> None:
        with pytest.raises(ValueError, match="CSV must contain a description column"):
            CSVFieldMapper.infer_mapping([])

    def test_raises_value_error_on_unmatched_columns(self) -> None:
        with pytest.raises(ValueError, match="CSV must contain a description column"):
            CSVFieldMapper.infer_mapping(["foo", "bar", "baz"])

    def test_raises_value_error_with_only_non_desc_cols(self) -> None:
        with pytest.raises(ValueError, match="CSV must contain a description column"):
            CSVFieldMapper.infer_mapping(["ticket_id", "priority", "status"])


class TestTicketIdAliases:
    """Verify ticket_id column matching (optional)."""

    @pytest.mark.parametrize(
        "col",
        [
            "ticket_id",
            "TICKET_ID",
            "Ticket_Id",
            "id",
            "ID",
            "case_id",
            "CASE_ID",
            "order_id",
            "ORDER_ID",
            "工单号",
            "工单编号",
        ],
    )
    def test_ticket_id_alias_matched(self, col: str) -> None:
        mapping = CSVFieldMapper.infer_mapping(["description", col])
        assert mapping.ticket_id_column == col

    def test_ticket_id_none_when_no_match(self) -> None:
        mapping = CSVFieldMapper.infer_mapping(["description", "comment"])
        assert mapping.ticket_id_column is None

    def test_ticket_id_optional_with_only_description(self) -> None:
        mapping = CSVFieldMapper.infer_mapping(["description"])
        assert mapping.ticket_id_column is None

    def test_both_columns_matched(self) -> None:
        mapping = CSVFieldMapper.infer_mapping(
            ["order_id", "problem_description", "extra"]
        )
        assert mapping.description_column == "problem_description"
        assert mapping.ticket_id_column == "order_id"


class TestInferMappingFromFile:
    """Test infer_mapping_from_file with actual CSV files."""

    def test_infers_from_csv_file(self, tmp_path: str) -> None:
        import pandas as pd

        csv_path = tmp_path / "test.csv"
        df = pd.DataFrame({"Description": ["line 1"], "Ticket_ID": ["T001"]})
        df.to_csv(csv_path, index=False)

        mapping = CSVFieldMapper.infer_mapping_from_file(csv_path)
        assert isinstance(mapping, CSVFieldMapping)
        assert mapping.description_column == "Description"
        assert mapping.ticket_id_column == "Ticket_ID"

    def test_raises_on_csv_without_description(self, tmp_path: str) -> None:
        import pandas as pd

        csv_path = tmp_path / "test.csv"
        df = pd.DataFrame({"foo": [1], "bar": [2]})
        df.to_csv(csv_path, index=False)

        with pytest.raises(ValueError, match="CSV must contain a description column"):
            CSVFieldMapper.infer_mapping_from_file(csv_path)
