import sqlite3
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from app.migrations import apply_migrations


def _now() -> str:
    return datetime.now(UTC).isoformat()


class IngestionJobStore:
    def __init__(self, database_path: str):
        from app.config import settings

        if settings.database_url:
            from app.postgres_stores import PostgresIngestionJobStore

            self._postgres = PostgresIngestionJobStore()
            return
        self.database_path = database_path
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ingestion_jobs (
                    job_id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL DEFAULT 'default',
                    workspace_id TEXT,
                    filename TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    content_type TEXT,
                    checksum TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(ingestion_jobs)"
                )
            }
            if "tenant_id" not in columns:
                connection.execute(
                    "ALTER TABLE ingestion_jobs ADD COLUMN tenant_id TEXT "
                    "NOT NULL DEFAULT 'default'"
                )
            additions = {
                "document_id": "TEXT",
                "workspace_id": "TEXT",
                "content_type": "TEXT",
                "checksum": "TEXT",
                "attempts": "INTEGER NOT NULL DEFAULT 0",
            }
            for name, definition in additions.items():
                if name not in columns:
                    connection.execute(
                        f"ALTER TABLE ingestion_jobs ADD COLUMN {name} {definition}"
                    )
            apply_migrations(connection)

    def __getattribute__(self, name):
        if name not in {"_postgres", "__dict__", "__class__"}:
            postgres = object.__getattribute__(self, "__dict__").get("_postgres")
            if postgres is not None and hasattr(postgres, name):
                return getattr(postgres, name)
        return object.__getattribute__(self, name)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def create(
        self,
        tenant_id: str,
        filename: str,
        file_path: Path,
        *,
        checksum: str | None = None,
        content_type: str | None = None,
        workspace_id: str | None = None,
    ) -> str:
        job_id = str(uuid4())
        document_id = str(uuid4())
        checksum = checksum or sha256(file_path.read_bytes()).hexdigest()
        timestamp = _now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO ingestion_jobs
                (job_id, document_id, tenant_id, workspace_id, filename, file_path,
                 content_type, checksum, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'queued', ?, ?)
                """,
                (
                    job_id,
                    document_id,
                    tenant_id,
                    workspace_id,
                    filename,
                    str(file_path),
                    content_type,
                    checksum,
                    timestamp,
                    timestamp,
                ),
            )
        return job_id

    def find_by_checksum(self, tenant_id: str, checksum: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM ingestion_jobs
                WHERE tenant_id = ? AND checksum = ?
                ORDER BY created_at DESC LIMIT 1
                """,
                (tenant_id, checksum),
            ).fetchone()
        return dict(row) if row else None

    def update(self, job_id: str, status: str, error: str | None = None) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE ingestion_jobs
                SET status = ?, error = ?, updated_at = ?
                WHERE job_id = ?
                """,
                (status, error, _now(), job_id),
            )

    def get(self, tenant_id: str, job_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM ingestion_jobs WHERE tenant_id = ? AND job_id = ?",
                (tenant_id, job_id),
            ).fetchone()
        return dict(row) if row else None

    def get_by_id(self, job_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM ingestion_jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
        return dict(row) if row else None

    def begin_attempt(self, job_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE ingestion_jobs
                SET status = 'processing', error = NULL,
                    attempts = attempts + 1, updated_at = ?
                WHERE job_id = ?
                """,
                (_now(), job_id),
            )

    def requeue(self, tenant_id: str, job_id: str) -> dict | None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE ingestion_jobs
                SET status = 'queued', error = NULL, updated_at = ?
                WHERE tenant_id = ? AND job_id = ?
                """,
                (_now(), tenant_id, job_id),
            )
        return self.get(tenant_id, job_id)

    def list_jobs(self, tenant_id: str, limit: int = 100) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM ingestion_jobs
                WHERE tenant_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (tenant_id, min(max(limit, 1), 100)),
            ).fetchall()
        return [dict(row) for row in rows]

    def delete(self, tenant_id: str, job_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                DELETE FROM ingestion_jobs
                WHERE tenant_id = ? AND job_id = ?
                """,
                (tenant_id, job_id),
            )
        return cursor.rowcount == 1
