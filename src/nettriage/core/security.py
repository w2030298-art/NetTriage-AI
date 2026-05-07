"""Cryptographic and path-safety helpers for NetTriage AI."""

import hashlib
import secrets
from datetime import UTC, datetime
from pathlib import Path


def hash_text(text: str) -> str:
    """Return the SHA-256 hex digest of *text*."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def safe_batch_id() -> str:
    """Generate a unique, human-readable batch identifier.

    Format: ``batch_YYYYMMDD_HHMMSS_<8 random hex chars>``.
    """
    now = datetime.now(UTC)
    suffix = secrets.token_hex(4)  # 8 hex chars
    return f"batch_{now:%Y%m%d_%H%M%S}_{suffix}"


def ensure_within_directory(base_dir: Path, target: Path) -> Path:
    """Resolve *target* and raise :class:`ValueError` if it escapes *base_dir*.

    Returns the resolved absolute path on success.
    """
    base = base_dir.resolve(strict=False)
    resolved = (base / target).resolve(strict=False)

    try:
        resolved.relative_to(base)
    except ValueError:
        raise ValueError(
            f"Path escapes base directory: target={target}, base={base_dir}"
        ) from None

    return resolved


def redact_text(text: str, max_chars: int = 80) -> str:
    """Truncate *text* to *max_chars* for safe display in logs / responses."""
    return text[:max_chars] if len(text) > max_chars else text
