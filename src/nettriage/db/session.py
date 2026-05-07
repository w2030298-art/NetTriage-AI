"""Database engine and session management for NetTriage AI."""

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import Engine
from sqlmodel import Session, create_engine
from sqlmodel.pool import StaticPool

from nettriage.core.config import Settings


def create_engine_from_settings(settings: Settings) -> Engine:
    """Build a SQLAlchemy Engine from application Settings.

    Creates parent directories for SQLite databases and configures
    connection pooling suitable for the backend.
    """
    db_url = settings.database_url

    if db_url.startswith("sqlite"):
        # Ensure directory exists for file-based SQLite
        db_path = db_url.removeprefix("sqlite:///")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    return create_engine(
        db_url,
        connect_args={"check_same_thread": False} if db_url.startswith("sqlite") else {},
        poolclass=StaticPool,  # Single connection — safe for SQLite + FastAPI
        echo=False,
    )


def get_session(engine: Engine) -> Generator[Session, None, None]:
    """Yield a :class:`sqlmodel.Session` tied to *engine*.

    Intended as a FastAPI dependency::

        def get_db() -> Generator[Session, None, None]:
            yield from get_session(engine)
    """
    with Session(engine) as session:
        yield session
