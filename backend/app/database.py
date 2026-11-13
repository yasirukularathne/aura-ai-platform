from pathlib import Path

import psycopg
from app.config import settings
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


def _sqlalchemy_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        return database_url.replace(
            "postgresql://",
            "postgresql+psycopg://",
            1,
        )
    return database_url


def get_engine() -> Engine | None:
    """Return the configured PostgreSQL engine, or None for SQLite development."""
    if not settings.database_url:
        return None
    return create_engine(
        _sqlalchemy_database_url(settings.database_url),
        pool_pre_ping=True,
    )


def check_database() -> bool:
    engine = get_engine()
    if engine is None:
        return True
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True


def ensure_postgres_schema() -> None:
    if not settings.database_url:
        return
    migration_dir = Path(__file__).parents[1] / "migrations"
    with psycopg.connect(settings.database_url) as connection:
        connection.execute("SELECT pg_advisory_lock(48190217)")
        try:
            _apply_postgres_migrations(connection, migration_dir)
        finally:
            connection.execute("SELECT pg_advisory_unlock(48190217)")


def _apply_postgres_migrations(connection, migration_dir: Path) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    for path in sorted(migration_dir.glob("*.sql")):
        version = path.stem
        if connection.execute(
            "SELECT 1 FROM schema_migrations WHERE version = %s",
            (version,),
        ).fetchone():
            continue
        connection.execute(path.read_text(encoding="utf-8"))
        connection.execute(
            "INSERT INTO schema_migrations (version) VALUES (%s)",
            (version,),
        )
