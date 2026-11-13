
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.migrations import apply_migrations


def _now() -> str:
    return datetime.now(UTC).isoformat()


class ConversationStore:
    def __init__(self, database_path: str):
        from app.config import settings

        if settings.database_url:
            from app.postgres_stores import PostgresConversationStore

            self._postgres = PostgresConversationStore()
            return

        self.database_path = database_path
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)

        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    conversation_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            apply_migrations(connection)

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_messages (
                    message_id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    citations TEXT,
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
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def create(
        self,
        tenant_id: str,
        title: str = "New conversation",
        workspace_id: str | None = None,
    ) -> dict:
        conversation_id = str(uuid4())
        timestamp = _now()

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO conversations (
                    conversation_id,
                    tenant_id,
                    workspace_id,
                    title,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    conversation_id,
                    tenant_id,
                    workspace_id,
                    title[:120],
                    timestamp,
                    timestamp,
                ),
            )

        return self.get(tenant_id, conversation_id, workspace_id)

    def get(
        self,
        tenant_id: str,
        conversation_id: str,
        workspace_id: str | None = None,
    ) -> dict | None:
        with self._connect() as connection:
            if workspace_id is not None:
                row = connection.execute(
                    """
                    SELECT conversation_id, workspace_id, title,
                           created_at, updated_at
                    FROM conversations
                    WHERE tenant_id = ?
                      AND conversation_id = ?
                      AND workspace_id = ?
                    """,
                    (tenant_id, conversation_id, workspace_id),
                ).fetchone()
            else:
                row = connection.execute(
                    """
                    SELECT conversation_id, workspace_id, title,
                           created_at, updated_at
                    FROM conversations
                    WHERE tenant_id = ? AND conversation_id = ?
                    """,
                    (tenant_id, conversation_id),
                ).fetchone()

        return dict(row) if row else None

    def list_conversations(
        self,
        tenant_id: str,
        limit: int = 50,
        offset: int = 0,
        workspace_id: str | None = None,
    ) -> list[dict]:
        with self._connect() as connection:
            if workspace_id is not None:
                rows = connection.execute(
                    """
                    SELECT conversation_id, workspace_id, title,
                           created_at, updated_at
                    FROM conversations
                    WHERE tenant_id = ? AND workspace_id = ?
                    ORDER BY updated_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (
                        tenant_id,
                        workspace_id,
                        min(max(limit, 1), 100),
                        max(offset, 0),
                    ),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT conversation_id, workspace_id, title,
                           created_at, updated_at
                    FROM conversations
                    WHERE tenant_id = ?
                    ORDER BY updated_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (
                        tenant_id,
                        min(max(limit, 1), 100),
                        max(offset, 0),
                    ),
                ).fetchall()

        return [dict(row) for row in rows]

    def rename(
        self,
        tenant_id: str,
        conversation_id: str,
        title: str,
        workspace_id: str | None = None,
    ) -> bool:
        with self._connect() as connection:
            if workspace_id is not None:
                cursor = connection.execute(
                    """
                    UPDATE conversations
                    SET title = ?, updated_at = ?
                    WHERE tenant_id = ?
                      AND conversation_id = ?
                      AND workspace_id = ?
                    """,
                    (title[:120], _now(), tenant_id, conversation_id, workspace_id),
                )
            else:
                cursor = connection.execute(
                    """
                    UPDATE conversations
                    SET title = ?, updated_at = ?
                    WHERE tenant_id = ? AND conversation_id = ?
                    """,
                    (title[:120], _now(), tenant_id, conversation_id),
                )

        return cursor.rowcount == 1

    def delete(
        self,
        tenant_id: str,
        conversation_id: str,
        workspace_id: str | None = None,
    ) -> bool:
        with self._connect() as connection:
            if workspace_id is not None:
                connection.execute(
                    """
                    DELETE FROM conversation_messages
                    WHERE tenant_id = ?
                      AND conversation_id = ?
                      AND EXISTS (
                          SELECT 1
                          FROM conversations
                          WHERE conversations.tenant_id = ?
                            AND conversations.conversation_id = ?
                            AND conversations.workspace_id = ?
                      )
                    """,
                    (
                        tenant_id,
                        conversation_id,
                        tenant_id,
                        conversation_id,
                        workspace_id,
                    ),
                )

                cursor = connection.execute(
                    """
                    DELETE FROM conversations
                    WHERE tenant_id = ?
                      AND conversation_id = ?
                      AND workspace_id = ?
                    """,
                    (tenant_id, conversation_id, workspace_id),
                )
            else:
                connection.execute(
                    """
                    DELETE FROM conversation_messages
                    WHERE tenant_id = ? AND conversation_id = ?
                    """,
                    (tenant_id, conversation_id),
                )

                cursor = connection.execute(
                    """
                    DELETE FROM conversations
                    WHERE tenant_id = ? AND conversation_id = ?
                    """,
                    (tenant_id, conversation_id),
                )

        return cursor.rowcount == 1

    def add_message(
        self,
        tenant_id: str,
        conversation_id: str,
        role: str,
        content: str,
        citations: str | None = None,
    ) -> None:
        timestamp = _now()

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO conversation_messages (
                    message_id,
                    conversation_id,
                    tenant_id,
                    role,
                    content,
                    citations,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    conversation_id,
                    tenant_id,
                    role,
                    content,
                    citations,
                    timestamp,
                ),
            )

            connection.execute(
                """
                UPDATE conversations
                SET updated_at = ?
                WHERE tenant_id = ? AND conversation_id = ?
                """,
                (timestamp, tenant_id, conversation_id),
            )

    def list_messages(
        self,
        tenant_id: str,
        conversation_id: str,
        workspace_id: str | None = None,
    ) -> list[dict]:
        with self._connect() as connection:
            if workspace_id is not None:
                rows = connection.execute(
                    """
                    SELECT m.message_id, m.role, m.content,
                           m.citations, m.created_at
                    FROM conversation_messages AS m
                    INNER JOIN conversations AS c
                        ON c.conversation_id = m.conversation_id
                       AND c.tenant_id = m.tenant_id
                    WHERE m.tenant_id = ?
                      AND m.conversation_id = ?
                      AND c.workspace_id = ?
                    ORDER BY m.created_at ASC
                    """,
                    (tenant_id, conversation_id, workspace_id),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT message_id, role, content, citations, created_at
                    FROM conversation_messages
                    WHERE tenant_id = ? AND conversation_id = ?
                    ORDER BY created_at ASC
                    """,
                    (tenant_id, conversation_id),
                ).fetchall()

        return [dict(row) for row in rows]
