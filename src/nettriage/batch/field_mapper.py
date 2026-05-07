"""CSV column inference — map user column names to the canonical fields.

Step 36: CSVFieldMapper
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from nettriage.schemas.batch import CSVFieldMapping

# ------------------------------------------------------------------ column alias tables

DESCRIPTION_ALIASES: frozenset[str] = frozenset(
    {
        "description",
        "desc",
        "content",
        "fault_description",
        "problem_description",
        "故障描述",
        "问题描述",
        "故障现象",
    }
)

TICKET_ID_ALIASES: frozenset[str] = frozenset(
    {
        "ticket_id",
        "id",
        "case_id",
        "order_id",
        "工单号",
        "工单编号",
    }
)

# ------------------------------------------------------------------ error messages

_CSV_DESCRIPTION_COLUMN_MISSING = (
    "CSV must contain a description column. "
    "Recognised names include: " + ", ".join(sorted(DESCRIPTION_ALIASES))
)


class CSVFieldMapper:
    """Infer which CSV columns map to the canonical description and ticket-id fields."""

    @staticmethod
    def infer_mapping(columns: list[str]) -> CSVFieldMapping:
        """Match *columns* against known aliases (case-insensitive).

        Args:
            columns: The column names from the CSV header.

        Returns:
            A :class:`CSVFieldMapping` with the matched column names.

        Raises:
            ValueError: If no description column can be matched.
        """
        lower_map = {c.lower(): c for c in columns}

        desc_col: str | None = None
        for alias in DESCRIPTION_ALIASES:
            key = alias.lower()
            if key in lower_map:
                desc_col = lower_map[key]
                break

        if desc_col is None:
            raise ValueError(_CSV_DESCRIPTION_COLUMN_MISSING)

        ticket_col: str | None = None
        for alias in TICKET_ID_ALIASES:
            key = alias.lower()
            if key in lower_map:
                ticket_col = lower_map[key]
                break

        return CSVFieldMapping(description_column=desc_col, ticket_id_column=ticket_col)

    @classmethod
    def infer_mapping_from_file(cls, input_path: Path) -> CSVFieldMapping:
        """Open *input_path*, read just the header row, and infer the field mapping.

        Args:
            input_path: Path to the CSV file.

        Returns:
            A :class:`CSVFieldMapping`.  Raises :class:`ValueError` on failure.
        """
        df = pd.read_csv(input_path, nrows=0)
        columns: list[str] = list(df.columns)
        return cls.infer_mapping(columns)
