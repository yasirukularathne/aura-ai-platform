import sqlite3
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row

from app.config import settings
from app.database import ensure_postgres_schema
from app.migrations import apply_migrations


class WorkspaceStore:
    def __init__(self, database_path: str | None = None):
        self.database_url = settings.database_url

        if self.database_url:
            ensure_postgres_schema()
            self.database_path = None
            return

        self.database_path = database_path or settings.database_path

        Path(self.database_path).parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with self._connect_sqlite() as connection:
            apply_migrations(connection)

    def _connect_sqlite(self) -> sqlite3.Connection:
        if not self.database_path:
            raise RuntimeError("SQLite database path is not configured")

        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def create(self, tenant_id: str, name: str) -> dict:
        tenant_id = tenant_id.strip()
        name = name.strip()

        if not tenant_id:
            raise ValueError("tenant_id cannot be empty")

        if not name:
            raise ValueError("Workspace name cannot be empty")

        workspace_id = str(uuid4())

        if self.database_url:
            with psycopg.connect(
                self.database_url,
                row_factory=dict_row,
            ) as connection:
                row = connection.execute(
                    """
                    INSERT INTO workspaces (
                        workspace_id,
                        tenant_id,
                        name
                    )
                    VALUES (%s, %s, %s)
                    RETURNING workspace_id, tenant_id, name, created_at
                    """,
                    (workspace_id, tenant_id, name),
                ).fetchone()

                return dict(row)

        with self._connect_sqlite() as connection:
            connection.execute(
                """
                INSERT INTO workspaces (
                    workspace_id,
                    tenant_id,
                    name
                )
                VALUES (?, ?, ?)
                """,
                (workspace_id, tenant_id, name),
            )

            row = connection.execute(
                """
                SELECT workspace_id, tenant_id, name, created_at
                FROM workspaces
                WHERE workspace_id = ?
                """,
                (workspace_id,),
            ).fetchone()

            return dict(row)

    def get(
        self,
        tenant_id: str,
        workspace_id: str,
    ) -> dict | None:
        if self.database_url:
            with psycopg.connect(
                self.database_url,
                row_factory=dict_row,
            ) as connection:
                row = connection.execute(
                    """
                    SELECT workspace_id, tenant_id, name, created_at
                    FROM workspaces
                    WHERE tenant_id = %s AND workspace_id = %s
                    """,
                    (tenant_id, workspace_id),
                ).fetchone()

                return dict(row) if row else None

        with self._connect_sqlite() as connection:
            row = connection.execute(
                """
                SELECT workspace_id, tenant_id, name, created_at
                FROM workspaces
                WHERE tenant_id = ? AND workspace_id = ?
                """,
                (tenant_id, workspace_id),
            ).fetchone()

            return dict(row) if row else None

    def belongs_to_tenant(
        self,
        tenant_id: str,
        workspace_id: str,
    ) -> bool:
        return self.get(tenant_id, workspace_id) is not None

    def list(self, tenant_id: str) -> list[dict]:
        if self.database_url:
            with psycopg.connect(
                self.database_url,
                row_factory=dict_row,
            ) as connection:
                rows = connection.execute(
                    """
                    SELECT workspace_id, tenant_id, name, created_at
                    FROM workspaces
                    WHERE tenant_id = %s
                    ORDER BY created_at DESC
                    """,
                    (tenant_id,),
                ).fetchall()

                return [dict(row) for row in rows]

        with self._connect_sqlite() as connection:
            rows = connection.execute(
                """
                SELECT workspace_id, tenant_id, name, created_at
                FROM workspaces
                WHERE tenant_id = ?
                ORDER BY created_at DESC
                """,
                (tenant_id,),
            ).fetchall()

            return [dict(row) for row in rows]