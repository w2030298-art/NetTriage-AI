"""Structured JSON-line logging for NetTriage AI."""

import logging
import sys
from datetime import UTC, datetime

from nettriage.core.config import Settings


class _RedactingFormatter(logging.Formatter):
    """JSON-line formatter that strips sensitive fields before output."""

    _SENSITIVE_KEYS = {"deepseek_api_key", "api_key", "password", "secret", "token"}

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, str | object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Attach extra context but never leak sensitive keys
        for key, value in record.__dict__.items():
            if key in self._SENSITIVE_KEYS:
                continue
            if key not in {
                "args",
                "asctime",
                "created",
                "exc_info",
                "exc_text",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "msg",
                "name",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "thread",
                "threadName",
            }:
                log_entry[key] = value

        return _safe_serialize(log_entry)


def _safe_serialize(entry: dict[str, str | object]) -> str:
    """Serialize a dict to a compact JSON line, falling back to repr on error."""
    import json

    try:
        return json.dumps(entry, default=str, separators=(",", ":"))
    except (TypeError, ValueError):
        return repr(entry)


def configure_logging(settings: Settings) -> None:
    """Wire up structured JSON-line logging for the root logger.

    Configures a single stream handler with the redacting formatter at the
    level specified in *settings*.  Existing handlers are removed first to
    avoid duplicate output when ``create_app`` is called multiple times in
    tests.
    """
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_RedactingFormatter())
    root.addHandler(handler)

    # Keep library loggers quieter
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
