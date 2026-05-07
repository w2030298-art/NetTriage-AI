"""Tests for BatchFileStore — Module H Step 35."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from fastapi import UploadFile

from nettriage.batch.file_store import BatchFileStore
from nettriage.core.config import Settings


@pytest.fixture
def file_store(tmp_path: Path) -> BatchFileStore:
    """Create a BatchFileStore that writes into a temporary directory."""
    settings = Settings(
        upload_dir=tmp_path / "uploads",
        export_dir=tmp_path / "exports",
        max_upload_mb=20,
    )
    return BatchFileStore(settings)


def _make_upload(filename: str, content: bytes) -> UploadFile:
    """Helper: create an UploadFile from bytes with the given filename."""
    return UploadFile(filename=filename, file=BytesIO(content))


class TestSaveValidCsv:
    def test_saves_csv_file(self, file_store: BatchFileStore) -> None:
        content = b"col1,col2\nval1,val2\n"
        upload = _make_upload("test.csv", content)
        batch_id = "batch_test_001"

        path = file_store.save_upload(batch_id, upload)

        assert path.exists()
        assert path.name == f"{batch_id}.csv"
        assert path.read_bytes() == content

    def test_saves_csv_with_uppercase_extension(self, file_store: BatchFileStore) -> None:
        content = b"desc\nhello\n"
        upload = _make_upload("DATA.CSV", content)
        path = file_store.save_upload("batch_UC", upload)
        assert path.exists()
        assert path.read_bytes() == content

    def test_creates_upload_directory(self, file_store: BatchFileStore) -> None:
        content = b"desc\nworld\n"
        upload = _make_upload("test.csv", content)
        path = file_store.save_upload("batch_dir", upload)
        assert path.parent.exists()
        assert path.parent.is_dir()

    def test_uses_batch_id_as_filename_not_original(self, file_store: BatchFileStore) -> None:
        """The stored filename must be the batch_id, never the original name."""
        content = b"desc\nx\n"
        upload = _make_upload("original_filename.csv", content)
        batch_id = "batch_SAFE_001"
        path = file_store.save_upload(batch_id, upload)
        assert path.name == f"{batch_id}.csv"
        assert "original_filename" not in path.name


class TestRejectNonCsv:
    def test_rejects_txt_file(self, file_store: BatchFileStore) -> None:
        upload = _make_upload("notes.txt", b"some text")
        with pytest.raises(ValueError, match="Only .csv files are accepted"):
            file_store.save_upload("batch_001", upload)

    def test_rejects_file_without_extension(self, file_store: BatchFileStore) -> None:
        upload = _make_upload("noext", b"data")
        with pytest.raises(ValueError, match="Only .csv files are accepted"):
            file_store.save_upload("batch_001", upload)

    def test_rejects_none_filename(self, file_store: BatchFileStore) -> None:
        upload = UploadFile(
            filename=None,  # type: ignore[arg-type]
            file=BytesIO(b"data"),
        )
        with pytest.raises(ValueError, match="Only .csv files are accepted"):
            file_store.save_upload("batch_001", upload)


class TestSizeCheck:
    def test_rejects_file_exceeding_limit(self, file_store: BatchFileStore) -> None:
        # Create content > 20 MB (default max_upload_mb)
        huge_content = b"x" * (21 * 1024 * 1024)  # 21 MB
        upload = _make_upload("big.csv", huge_content)
        with pytest.raises(ValueError, match="exceeds limit"):
            file_store.save_upload("batch_001", upload)

    def test_accepts_file_at_limit(self, file_store: BatchFileStore) -> None:
        content = b"x" * (20 * 1024 * 1024)  # exactly 20 MB
        upload = _make_upload("at_limit.csv", content)
        path = file_store.save_upload("batch_at_limit", upload)
        assert path.exists()

    def test_respects_custom_limit(self, tmp_path: Path) -> None:
        settings = Settings(
            upload_dir=tmp_path / "u",
            max_upload_mb=1,
        )
        store = BatchFileStore(settings)
        content = b"x" * (2 * 1024 * 1024)  # 2 MB
        upload = _make_upload("test.csv", content)
        with pytest.raises(ValueError, match="exceeds limit"):
            store.save_upload("b", upload)


class TestPathMethods:
    def test_get_input_path(self, file_store: BatchFileStore) -> None:
        path = file_store.get_input_path("batch_X")
        assert path.name == "batch_X.csv"
        assert path.is_absolute()

    def test_get_output_path(self, file_store: BatchFileStore) -> None:
        path = file_store.get_output_path("batch_X")
        assert path.name == "batch_X_results.csv"
        assert path.is_absolute()
