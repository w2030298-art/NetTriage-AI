"""Unit tests for nettriage.core.security helpers."""

import hashlib
from pathlib import Path

import pytest

from nettriage.core.security import (
    ensure_within_directory,
    hash_text,
    redact_text,
    safe_batch_id,
)


class TestHashText:
    def test_consistent_output(self) -> None:
        """Same input produces the same hex digest."""
        assert hash_text("hello") == hash_text("hello")

    def test_different_inputs_produce_different_digests(self) -> None:
        """Different inputs produce different digests."""
        assert hash_text("hello") != hash_text("world")

    def test_uses_sha256(self) -> None:
        """Output matches Python's own hashlib.sha256."""
        expected = hashlib.sha256(b"test").hexdigest()
        assert hash_text("test") == expected


class TestSafeBatchId:
    def test_format(self) -> None:
        """Generated ID matches the expected pattern."""
        bid = safe_batch_id()
        assert bid.startswith("batch_")
        # batch_YYYYMMDD_HHMMSS_<8hex>
        parts = bid.split("_")
        assert len(parts) == 4  # batch, date, time, hex
        assert len(parts[1]) == 8  # YYYYMMDD
        assert len(parts[2]) == 6  # HHMMSS
        assert len(parts[3]) == 8  # 8 hex

    def test_uniqueness(self) -> None:
        """Consecutive calls produce different IDs."""
        ids = {safe_batch_id() for _ in range(20)}
        assert len(ids) == 20


class TestEnsureWithinDirectory:
    def test_valid_child_path(self) -> None:
        """A child path inside the base is returned resolved."""
        base = Path("/tmp/test-base")
        result = ensure_within_directory(base, Path("sub/file.txt"))
        assert result == (base / "sub/file.txt").resolve()

    def test_current_directory_is_allowed(self) -> None:
        """The base directory itself (target='.') is allowed."""
        base = Path("/tmp/test-base")
        result = ensure_within_directory(base, Path("."))
        assert result == base.resolve()

    def test_traversal_attempt_raises(self) -> None:
        """Path traversal (../../etc) raises ValueError."""
        base = Path("/tmp/test-base")
        with pytest.raises(ValueError, match="escapes base directory"):
            ensure_within_directory(base, Path("../../../etc/passwd"))

    def test_absolute_target_outside_base_raises(self) -> None:
        """An absolute target outside the base raises ValueError."""
        base = Path("/tmp/test-base")
        with pytest.raises(ValueError, match="escapes base directory"):
            ensure_within_directory(base, Path("/etc/passwd"))


class TestRedactText:
    def test_short_text_is_unchanged(self) -> None:
        """Text shorter than max_chars returns as-is."""
        assert redact_text("hello", max_chars=80) == "hello"

    def test_exact_length_is_unchanged(self) -> None:
        """Text exactly at max_chars returns as-is."""
        assert redact_text("a" * 80, max_chars=80) == "a" * 80

    def test_long_text_is_truncated(self) -> None:
        """Text longer than max_chars is truncated."""
        assert redact_text("a" * 100, max_chars=80) == "a" * 80

    def test_default_max_chars(self) -> None:
        """Default max_chars is 80."""
        assert redact_text("a" * 200) == "a" * 80
