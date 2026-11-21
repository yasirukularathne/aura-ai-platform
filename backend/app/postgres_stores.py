
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import psycopg
from app.config import settings
from psycopg.rows import dict_row


def _connect():
    return psycopg.connect(settings.database_url, row_factory=dict_row)


class PostgresApiKeyStore:
    def __init__(self):
        from app.database import ensure_postgres_schema

        ensure_postgres_schema()

    @staticmethod
    def _hash(raw_key: str) -> str:
        from app.auth import password_hasher

        return password_hasher.hash(raw_key)

    @staticmethod
    def _verify(stored_hash: str, raw_key: str) -> bool:
        from app.auth import ApiKeyStore

        return ApiKeyStore._verify_hash(stored_hash, raw_key)

    def ensure_bootstrap_key(self) -> None:
        if not settings.api_key:
            return
        with _connect() as connection:
            rows = connection.execute(
                "SELECT key_hash FROM api_keys WHERE tenant_id = %s AND role = 'admin'",
                (settings.tenant_id,),
            ).fetchall()
            if any(self._verify(row["key_hash"], settings.api_key) for row in rows):
                return
            connection.execute(
                """
                INSERT INTO api_keys
                (key_id, key_hash, tenant_id, role, expires_at)
                VALUES (%s, %s, %s, 'admin', NULL)
                ON CONFLICT (key_id) DO NOTHING
                """,
                (str(uuid4()), self._hash(settings.api_key), settings.tenant_id),
            )

    def create(self, tenant_id: str, role: str, expires_at: str | None = None):
        raw_key = secrets.token_urlsafe(32)
        key_id = str(uuid4())
        with _connect() as connection:
            connection.execute(
                """
                INSERT INTO api_keys
                (key_id, key_hash, tenant_id, role, expires_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (key_id, self._hash(raw_key), tenant_id, role, expires_at),
            )
        return key_id, raw_key

    def authenticate(self, raw_key: str):
        self.ensure_bootstrap_key()
        with _connect() as connection:
            rows = connection.execute(
                """
                SELECT key_id, key_hash, tenant_id, role, expires_at
                FROM api_keys WHERE active = TRUE
                """
            ).fetchall()
        for row in rows:
            if self._verify(row["key_hash"], raw_key):
                if row["expires_at"] and row["expires_at"] <= datetime.now(UTC):
                    continue
                return {
                    "key_id": row["key_id"],
                    "tenant_id": row["tenant_id"],
                    "role": row["role"],
                }
        return None

    def rotate(self, tenant_id: str, key_id: str):
        raw_key = secrets.token_urlsafe(32)
        with _connect() as connection:
            result = connection.execute(
                """
                UPDATE api_keys
                SET key_hash = %s, created_at = now(), expires_at = %s
                WHERE key_id = %s
                  AND tenant_id = %s
                  AND active = TRUE
                """,
                (
                    self._hash(raw_key),
                    datetime.now(UTC) + timedelta(days=settings.api_key_ttl_days),
                    key_id,
                    tenant_id,
                ),
            )
        return (key_id, raw_key) if result.rowcount == 1 else None

    def revoke(self, tenant_id: str, key_id: str) -> bool:
        with _connect() as connection:
            result = connection.execute(
                """
                UPDATE api_keys
                SET active = FALSE
                WHERE key_id = %s AND tenant_id = %s
                """,
                (key_id, tenant_id),
            )
        return result.rowcount == 1

    def consume_rate_limit(self, key_id, bucket, limit, window_seconds=60):
        now = int(datetime.now(UTC).timestamp())
        window_start = now - (now % window_seconds)
        with _connect() as connection:
            row = connection.execute(
                """
                SELECT window_start, request_count
                FROM rate_limit_windows
                WHERE key_id = %s AND bucket = %s
                FOR UPDATE
                """,
                (key_id, bucket),
            ).fetchone()
            count = (
                row["request_count"] + 1
                if row and row["window_start"] == window_start
                else 1
            )
            connection.execute(
                """
                INSERT INTO rate_limit_windows
                (key_id, bucket, window_start, request_count)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (key_id, bucket) DO UPDATE SET
                    window_start = EXCLUDED.window_start,
                    request_count = EXCLUDED.request_count
                """,
                (key_id, bucket, window_start, count),
            )
        return count <= limit, max(1, window_start + window_seconds - now)

    def audit(self, tenant_id, actor_key_id, action, resource, details=None):
        with _connect() as connection:
            connection.execute(
                """
                INSERT INTO audit_events
                (event_id, tenant_id, actor_key_id, action, resource, details, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(uuid4()), tenant_id, actor_key_id, action, resource,
                    details, datetime.now(UTC),
                ),
            )

    def list_audit_events(self, tenant_id, limit=100):
        with _connect() as connection:
            return connection.execute(
                """
                SELECT event_id, actor_key_id, action, resource, details, created_at
                FROM audit_events WHERE tenant_id = %s
                ORDER BY created_at DESC LIMIT %s
                """,
                (tenant_id, limit),
            ).fetchall()


class PostgresConversationStore:
    def __init__(self):
        from app.database import ensure_postgres_schema

        ensure_postgres_schema()

    def create(self, tenant_id, title="New conversation", workspace_id=None):
        conversation_id = str(uuid4())
        with _connect() as connection:
            connection.execute(
                """
                INSERT INTO conversations
                (conversation_id, tenant_id, workspace_id, title)
                VALUES (%s, %s, %s, %s)
                """,
                (conversation_id, tenant_id, workspace_id, title[:120]),
            )
        return self.get(tenant_id, conversation_id, workspace_id)

    def get(self, tenant_id, conversation_id, workspace_id=None):
        with _connect() as connection:
            if workspace_id is None:
                return connection.execute(
                    """
                    SELECT conversation_id, tenant_id, workspace_id,
                           title, created_at, updated_at
                    FROM conversations
                    WHERE tenant_id = %s AND conversation_id = %s
                    """,
                    (tenant_id, conversation_id),
                ).fetchone()

            return connection.execute(
                """
                SELECT conversation_id, tenant_id, workspace_id,
                       title, created_at, updated_at
                FROM conversations
                WHERE tenant_id = %s
                  AND conversation_id = %s
                  AND workspace_id = %s
                """,
                (tenant_id, conversation_id, workspace_id),
            ).fetchone()

    def list_conversations(
        self,
        tenant_id,
        limit=50,
        offset=0,
        workspace_id=None,
    ):
        with _connect() as connection:
            if workspace_id is None:
                return connection.execute(
                    """
                    SELECT conversation_id, tenant_id, workspace_id,
                           title, created_at, updated_at
                    FROM conversations
                    WHERE tenant_id = %s
                    ORDER BY updated_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (
                        tenant_id,
                        min(max(limit, 1), 100),
                        max(offset, 0),
                    ),
                ).fetchall()

            return connection.execute(
                """
                SELECT conversation_id, tenant_id, workspace_id,
                       title, created_at, updated_at
                FROM conversations
                WHERE tenant_id = %s AND workspace_id = %s
                ORDER BY updated_at DESC
                LIMIT %s OFFSET %s
                """,
                (
                    tenant_id,
                    workspace_id,
                    min(max(limit, 1), 100),
                    max(offset, 0),
                ),
            ).fetchall()

    def rename(
        self,
        tenant_id,
        conversation_id,
        title,
        workspace_id=None,
    ):
        with _connect() as connection:
            if workspace_id is None:
                result = connection.execute(
                    """
                    UPDATE conversations
                    SET title = %s, updated_at = now()
                    WHERE tenant_id = %s AND conversation_id = %s
                    """,
                    (title[:120], tenant_id, conversation_id),
                )
            else:
                result = connection.execute(
                    """
                    UPDATE conversations
                    SET title = %s, updated_at = now()
                    WHERE tenant_id = %s
                      AND conversation_id = %s
                      AND workspace_id = %s
                    """,
                    (title[:120], tenant_id, conversation_id, workspace_id),
                )
        return result.rowcount == 1

    def delete(self, tenant_id, conversation_id, workspace_id=None):
        with _connect() as connection:
            if workspace_id is None:
                result = connection.execute(
                    """
                    DELETE FROM conversations
                    WHERE tenant_id = %s AND conversation_id = %s
                    """,
                    (tenant_id, conversation_id),
                )
            else:
                result = connection.execute(
                    """
                    DELETE FROM conversations
                    WHERE tenant_id = %s
                      AND conversation_id = %s
                      AND workspace_id = %s
                    """,
                    (tenant_id, conversation_id, workspace_id),
                )
        return result.rowcount == 1

    def add_message(
        self,
        tenant_id,
        conversation_id,
        role,
        content,
        citations=None,
    ):
        with _connect() as connection:
            connection.execute(
                """
                INSERT INTO conversation_messages
                (message_id, conversation_id, tenant_id, role, content, citations)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                """,
                (
                    str(uuid4()), conversation_id, tenant_id, role, content,
                    citations,
                ),
            )
            connection.execute(
                """
                UPDATE conversations SET updated_at = now()
                WHERE tenant_id = %s AND conversation_id = %s
                """,
                (tenant_id, conversation_id),
            )

    def list_messages(
        self,
        tenant_id,
        conversation_id,
        workspace_id=None,
    ):
        with _connect() as connection:
            if workspace_id is None:
                return connection.execute(
                    """
                    SELECT message_id, role, content, citations, created_at
                    FROM conversation_messages
                    WHERE tenant_id = %s AND conversation_id = %s
                    ORDER BY created_at ASC
                    """,
                    (tenant_id, conversation_id),
                ).fetchall()

            return connection.execute(
                """
                SELECT messages.message_id, messages.role, messages.content,
                       messages.citations, messages.created_at
                FROM conversation_messages AS messages
                INNER JOIN conversations AS conversations
                    ON conversations.conversation_id = messages.conversation_id
                   AND conversations.tenant_id = messages.tenant_id
                WHERE messages.tenant_id = %s
                  AND messages.conversation_id = %s
                  AND conversations.workspace_id = %s
                ORDER BY messages.created_at ASC
                """,
                (tenant_id, conversation_id, workspace_id),
            ).fetchall()


class PostgresIngestionJobStore:
    def __init__(self):
        from app.database import ensure_postgres_schema

        ensure_postgres_schema()

    def create(self, tenant_id, filename, file_path: Path, *, checksum=None,
               content_type=None, workspace_id=None):
        from hashlib import sha256

        job_id = str(uuid4())
        document_id = str(uuid4())
        checksum = checksum or sha256(file_path.read_bytes()).hexdigest()
        with _connect() as connection:
            connection.execute(
                """
                INSERT INTO ingestion_jobs
                (job_id, document_id, tenant_id, workspace_id, filename, file_path,
                 storage_key, content_type, checksum, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'queued')
                """,
                (
                    job_id, document_id, tenant_id, workspace_id, filename,
                    str(file_path), str(file_path), content_type, checksum,
                ),
            )
        return job_id

    def find_by_checksum(self, tenant_id, checksum):
        with _connect() as connection:
            return connection.execute(
                """
                SELECT * FROM ingestion_jobs
                WHERE tenant_id = %s AND checksum = %s
                ORDER BY created_at DESC LIMIT 1
                """,
                (tenant_id, checksum),
            ).fetchone()

    def update(self, job_id, status, error=None):
        with _connect() as connection:
            connection.execute(
                """
                UPDATE ingestion_jobs
                SET status = %s, error = %s, updated_at = now()
                WHERE job_id = %s
                """,
                (status, error, job_id),
            )

    def get(self, tenant_id, job_id):
        with _connect() as connection:
            return connection.execute(
                "SELECT * FROM ingestion_jobs WHERE tenant_id = %s AND job_id = %s",
                (tenant_id, job_id),
            ).fetchone()

    def get_by_id(self, job_id):
        with _connect() as connection:
            return connection.execute(
                "SELECT * FROM ingestion_jobs WHERE job_id = %s",
                (job_id,),
            ).fetchone()

    def begin_attempt(self, job_id):
        with _connect() as connection:
            connection.execute(
                """
                UPDATE ingestion_jobs
                SET status = 'processing', error = NULL,
                    attempts = attempts + 1, updated_at = now()
                WHERE job_id = %s
                """,
                (job_id,),
            )

    def requeue(self, tenant_id, job_id):
        with _connect() as connection:
            connection.execute(
                """
                UPDATE ingestion_jobs SET status = 'queued', error = NULL,
                    updated_at = now()
                WHERE tenant_id = %s AND job_id = %s
                """,
                (tenant_id, job_id),
            )
        return self.get(tenant_id, job_id)

    def list_jobs(self, tenant_id, limit=100):
        with _connect() as connection:
            return connection.execute(
                """
                SELECT * FROM ingestion_jobs WHERE tenant_id = %s
                ORDER BY created_at DESC LIMIT %s
                """,
                (tenant_id, min(max(limit, 1), 100)),
            ).fetchall()

    def delete(self, tenant_id, job_id):
        with _connect() as connection:
            result = connection.execute(
                "DELETE FROM ingestion_jobs WHERE tenant_id = %s AND job_id = %s",
                (tenant_id, job_id),
            )
        return result.rowcount == 1
