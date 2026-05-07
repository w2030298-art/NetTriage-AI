"""Batch file storage — save and validate uploaded CSV files.

Step 35: BatchFileStore
"""

from __future__ import annotations

from pathlib import Path

from fastapi import UploadFile

from nettriage.core.config import Settings


class BatchFileStore:
    """Manage uploaded batch CSV files on disk.

    Files are stored under ``settings.upload_dir`` using the batch_id
    as the filename — never the original upload name.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    # ------------------------------------------------------------------ public API

    def save_upload(self, batch_id: str, upload_file: UploadFile) -> Path:
        """Validate and persist *upload_file* as ``{batch_id}.csv``.

        Args:
            batch_id: Unique batch identifier (used as the stored filename).
            upload_file: The incoming file from the HTTP request.

        Returns:
            The absolute :class:`Path` to the saved file.

        Raises:
            ValueError: If the file extension is not ``.csv`` or the file
                exceeds ``settings.max_upload_mb``.
        """
        # --- extension check (use original filename only for validation) ---
        if not upload_file.filename or not upload_file.filename.lower().endswith(".csv"):
            raise ValueError(
                f"Only .csv files are accepted, got: {upload_file.filename!r}"
            )

        # --- size check ---
        # Starlette / FastAPI UploadFile wraps a SpooledTemporaryFile which
        # supports ``seek``.  We read the whole content into memory *once*
        # for validation and persisting.
        content = upload_file.file.read()
        size_mb = len(content) / (1024 * 1024)
        if size_mb > self._settings.max_upload_mb:
            raise ValueError(
                f"Upload size {size_mb:.2f} MB exceeds limit "
                f"of {self._settings.max_upload_mb} MB"
            )

        # --- ensure upload directory exists ---
        self._settings.upload_dir.mkdir(parents=True, exist_ok=True)

        # --- write using batch_id as filename ---
        dest_path = self.get_input_path(batch_id)
        dest_path.write_bytes(content)

        return dest_path

    def get_input_path(self, batch_id: str) -> Path:
        """Return the absolute path where the batch input CSV is (or will be) stored."""
        return (self._settings.upload_dir / f"{batch_id}.csv").resolve()

    def get_output_path(self, batch_id: str) -> Path:
        """Return the absolute path where the batch output CSV is (or will be) stored.

        Note: the output is managed by :class:`ResultCSVExporter`; this method
        is provided as a convenience for consumers that need to locate the file.
        """
        return (self._settings.export_dir / f"{batch_id}_results.csv").resolve()
