"""Batch result CSV exporter — streaming write with JSON-serialised compound fields.

Step 37: ResultCSVExporter
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from nettriage.core.config import Settings

# ------------------------------------------------------------------ output schema

_OUTPUT_COLUMNS = (
    "ticket_id",
    "primary_category",
    "secondary_categories",
    "confidence",
    "review_required",
    "review_reasons",
    "key_symptoms",
    "summary",
    "troubleshooting_steps",
    "llm_model",
    "llm_latency_ms",
    "processed_at",
    "error",
)

# Fields whose values are lists or dicts and must be serialised as JSON strings
_JSON_FIELDS: frozenset[str] = frozenset(
    {
        "secondary_categories",
        "review_reasons",
        "key_symptoms",
        "troubleshooting_steps",
    }
)


class ResultCSVExporter:
    """Create and incrementally populate batch result CSV files.

    Output files are placed under ``settings.export_dir``.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        # Cache open writers keyed by batch_id for streaming performance.
        self._writers: dict[str, tuple[Any, csv.DictWriter[str]]] = {}

    # ------------------------------------------------------------------ public API

    def create_output(self, batch_id: str) -> Path:
        """Create a new output CSV (with header) for *batch_id* and return its path.

        If the file already exists it will be **overwritten**.
        """
        path = self.get_output_path(batch_id)
        path.parent.mkdir(parents=True, exist_ok=True)

        f = open(path, "w", newline="", encoding="utf-8")  # noqa: SIM115 — cached for streaming
        writer = csv.DictWriter(f, fieldnames=_OUTPUT_COLUMNS)
        writer.writeheader()
        f.flush()

        self._writers[batch_id] = (f, writer)
        return path

    def append_row(self, batch_id: str, row: dict[str, Any]) -> None:
        """Append a single result row to the batch output CSV.

        List / dict values are JSON-serialised before writing.
        The file is flushed after each row so partial results survive a crash.

        Args:
            batch_id: The batch whose output file should receive the row.
            row: Flat dict whose keys correspond to ``_OUTPUT_COLUMNS``.

        Raises:
            KeyError: If *batch_id* has no open writer (call ``create_output`` first).
        """
        f, writer = self._writers[batch_id]

        # Serialise compound fields
        serialised: dict[str, str] = {}
        for key in _OUTPUT_COLUMNS:
            value = row.get(key, "")
            if key in _JSON_FIELDS and not isinstance(value, str):
                serialised[key] = json.dumps(value, ensure_ascii=False)
            else:
                serialised[key] = str(value) if value != "" else ""

        writer.writerow(serialised)
        f.flush()

    def finalize(self, batch_id: str) -> None:
        """Close the output file for *batch_id* and release resources."""
        entry = self._writers.pop(batch_id, None)
        if entry is not None:
            entry[0].close()

    def get_output_path(self, batch_id: str) -> Path:
        """Return the absolute path for the batch result CSV."""
        return (self._settings.export_dir / f"{batch_id}_results.csv").resolve()
