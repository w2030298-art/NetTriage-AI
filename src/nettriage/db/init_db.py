"""Database initialisation — table creation and SQLite PRAGMAs."""

import logging

from sqlalchemy import Engine, event
from sqlmodel import SQLModel

logger = logging.getLogger(__name__)


def _set_sqlite_pragmas(dbapi_connection: object, _connection_record: object) -> None:
    """Apply performance / safety PRAGMAs to every new SQLite connection."""
    cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.execute("PRAGMA busy_timeout=5000;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.close()


def init_db(engine: Engine) -> None:
    """Create all tables and register SQLite PRAGMAs on *engine*."""
    # Register PRAGMA listener for every new connection (idempotent).
    event.listen(engine, "connect", _set_sqlite_pragmas)

    # Import models so SQLModel.metadata knows about them.
    import nettriage.db.models  # noqa: F401  # side-effect: registers tables

    SQLModel.metadata.create_all(engine)
    logger.info("Database tables created successfully")
