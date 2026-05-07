"""Shared pytest fixtures for NetTriage AI tests."""

import os
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from nettriage.api.dependencies import _get_engine, get_llm_client
from nettriage.api.main import create_app
from nettriage.core.config import get_settings
from nettriage.db.init_db import init_db
from tests.fakes import FakeLLMClient


@pytest.fixture
def temp_db() -> Generator[str, None, None]:
    """Create a temporary SQLite database file and return its path."""
    fd, path = tempfile.mkstemp(suffix=".db", prefix="nettriage_api_test_")
    os.close(fd)
    yield path
    for suffix in ("", "-wal", "-shm"):
        p = Path(path + suffix)
        try:
            if p.exists():
                p.unlink()
        except PermissionError:
            pass  # Windows: SQLite may still hold file locks briefly


@pytest.fixture
def fake_llm_client() -> FakeLLMClient:
    """Provide a FakeLLMClient instance for dependency override."""
    return FakeLLMClient()


@pytest.fixture
def test_client(
    temp_db: str,
    fake_llm_client: FakeLLMClient,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[TestClient, None, None]:
    """Provide a synchronous FastAPI TestClient with FakeLLMClient override.

    Uses a temp SQLite database with full schema.
    """
    db_url = f"sqlite:///{temp_db}"
    monkeypatch.setenv("DATABASE_URL", db_url)

    # Clear cached singletons so Settings/Engine picks up the temp DB URL
    get_settings.cache_clear()
    _get_engine.cache_clear()

    # Create tables on the temp database before the app starts
    init_db(_get_engine())

    app = create_app()
    app.dependency_overrides[get_llm_client] = lambda: fake_llm_client
    with TestClient(app) as client:
        yield client
