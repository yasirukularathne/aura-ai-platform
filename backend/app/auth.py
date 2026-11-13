
import secrets
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from app.config import settings
from app.migrations import apply_migrations
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

password_hasher = PasswordHasher()
redis_client = None
if settings.redis_url:
    from redis import Redis

    redis_client = Redis.from_url(settings.redis_url, decode_responses=True)


class ApiKeyStore:
    def __init__(self, database_path: str):
        if settings.database_url:
            from app.postgres_stores import PostgresApiKeyStore

            self._postgres = PostgresApiKeyStore()
            return
        self.database_path = database_path
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS api_keys (
                    key_id TEXT PRIMARY KEY,
                    key_hash TEXT UNIQUE NOT NULL,
                    tenant_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    expires_at TEXT
                )
                """
            )
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(api_keys)")
            }
            if "expires_at" not in columns:
                connection.execute("ALTER TABLE api_keys ADD COLUMN expires_at TEXT")
            apply_migrations(connection)
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS rate_limit_windows (
                    key_id TEXT NOT NULL,
                    bucket TEXT NOT NULL,
                    window_start INTEGER NOT NULL,
                    request_count INTEGER NOT NULL,
                    PRIMARY KEY (key_id, bucket)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    actor_key_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    details TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )

    def __getattribute__(self, name):
        if name not in {"_postgres", "__dict__", "__class__"}:
            postgres = object.__getattribute__(self, "__dict__").get("_postgres")
            if postgres is not None and hasattr(postgres, name):
                return getattr(postgres, name)
        return object.__getattribute__(self, name)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database_path)

    @staticmethod
    def _hash(raw_key: str) -> str:
        return password_hasher.hash(raw_key)

    def ensure_bootstrap_key(self) -> None:
        if settings.api_key:
            with self._connect() as connection:
                connection.row_factory = sqlite3.Row
                existing = connection.execute(
                    "SELECT key_hash FROM api_keys WHERE tenant_id = ? AND role = 'admin'",
                    (settings.tenant_id,),
                ).fetchall()
                if any(
                    self._verify_hash(row["key_hash"], settings.api_key)
                    for row in existing
                ):
                    return
                connection.execute(
                    """
                    INSERT OR IGNORE INTO api_keys
                    (key_id, key_hash, tenant_id, role, expires_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid4()),
                        self._hash(settings.api_key),
                        settings.tenant_id,
                        "admin",
                        None,
                    ),
                )

    @staticmethod
    def _verify_hash(stored_hash: str, raw_key: str) -> bool:
        try:
            return password_hasher.verify(stored_hash, raw_key)
        except (VerifyMismatchError, InvalidHashError):
            return False

    def create(
        self,
        tenant_id: str,
        role: str,
        expires_at: str | None = None,
    ) -> tuple[str, str]:
        raw_key = secrets.token_urlsafe(32)
        key_id = str(uuid4())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO api_keys
                (key_id, key_hash, tenant_id, role, expires_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (key_id, self._hash(raw_key), tenant_id, role, expires_at),
            )
        return key_id, raw_key

    def authenticate(self, raw_key: str) -> dict | None:
        self.ensure_bootstrap_key()
        with self._connect() as connection:
            connection.row_factory = sqlite3.Row
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT key_id, key_hash, tenant_id, role, expires_at
                FROM api_keys
                WHERE active = 1
                """,
            ).fetchall()
        for row in rows:
            if not self._verify_hash(row["key_hash"], raw_key):
                continue
            if row["expires_at"] and row["expires_at"] <= datetime.now(UTC).isoformat():
                continue
            return {
                "key_id": row["key_id"],
                "tenant_id": row["tenant_id"],
                "role": row["role"],
            }
        return None

    def rotate(self, tenant_id: str, key_id: str) -> tuple[str, str] | None:
        raw_key = secrets.token_urlsafe(32)
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE api_keys
                SET key_hash = ?, created_at = CURRENT_TIMESTAMP,
                    expires_at = ?
                WHERE key_id = ?
                  AND tenant_id = ?
                  AND active = 1
                """,
                (
                    self._hash(raw_key),
                    (
                        datetime.now(UTC) + timedelta(days=settings.api_key_ttl_days)
                    ).isoformat(),
                    key_id,
                    tenant_id,
                ),
            )
        return (key_id, raw_key) if cursor.rowcount == 1 else None

    def revoke(self, tenant_id: str, key_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE api_keys
                SET active = 0
                WHERE key_id = ? AND tenant_id = ?
                """,
                (key_id, tenant_id),
            )
        return cursor.rowcount == 1

    def consume_rate_limit(
        self,
        key_id: str,
        bucket: str,
        limit: int,
        window_seconds: int = 60,
    ) -> tuple[bool, int]:
        now = int(datetime.now(UTC).timestamp())
        window_start = now - (now % window_seconds)
        if redis_client is not None:
            key = f"aura:rate:{key_id}:{bucket}:{window_start}"
            try:
                count = int(redis_client.incr(key))
                if count == 1:
                    redis_client.expire(key, window_seconds)
                return (
                    count <= limit,
                    max(1, window_start + window_seconds - now),
                )
            except Exception:
                # Local/database fallback keeps the API available if Redis is down.
                pass
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT window_start, request_count
                FROM rate_limit_windows
                WHERE key_id = ? AND bucket = ?
                """,
                (key_id, bucket),
            ).fetchone()
            count = row[1] + 1 if row and row[0] == window_start else 1
            connection.execute(
                """
                INSERT INTO rate_limit_windows
                (key_id, bucket, window_start, request_count)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key_id, bucket) DO UPDATE SET
                    window_start = excluded.window_start,
                    request_count = excluded.request_count
                """,
                (key_id, bucket, window_start, count),
            )
        return count <= limit, max(1, window_start + window_seconds - now)

    def audit(
        self,
        tenant_id: str,
        actor_key_id: str,
        action: str,
        resource: str,
        details: str | None = None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO audit_events
                (event_id, tenant_id, actor_key_id, action, resource, details, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    tenant_id,
                    actor_key_id,
                    action,
                    resource,
                    details,
                    datetime.now(UTC).isoformat(),
                ),
            )

    def list_audit_events(self, tenant_id: str, limit: int = 100) -> list[dict]:
        with self._connect() as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT event_id, actor_key_id, action, resource, details, created_at
                FROM audit_events
                WHERE tenant_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (tenant_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]


def require_role(request, *allowed_roles: str) -> None:
    if request.state.role not in allowed_roles:
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Insufficient role")
