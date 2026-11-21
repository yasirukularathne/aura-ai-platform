import sqlite3
from collections.abc import Callable

Migration = tuple[int, Callable[[sqlite3.Connection], None]]


def _migration_one(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA user_version = 1")


def _migration_two(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS workspaces (
            workspace_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_workspaces_tenant_created
        ON workspaces (tenant_id, created_at DESC)
        """
    )

    connection.execute("PRAGMA user_version = 2")


def _migration_three(connection: sqlite3.Connection) -> None:
    columns = {
        row[1]
        for row in connection.execute(
            "PRAGMA table_info(conversations)"
        ).fetchall()
    }

    if "workspace_id" not in columns:
        connection.execute(
            "ALTER TABLE conversations ADD COLUMN workspace_id TEXT"
        )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_conversations_tenant_workspace
        ON conversations (tenant_id, workspace_id, updated_at DESC)
        """
    )

    connection.execute("PRAGMA user_version = 3")


def apply_migrations(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    migrations: list[Migration] = [
        (1, _migration_one),
        (2, _migration_two),
        (3, _migration_three),
    ]

    for version, migration in migrations:
        applied = connection.execute(
            "SELECT 1 FROM schema_migrations WHERE version = ?",
            (version,),
        ).fetchone()

        if applied:
            continue

        # Migration 3 requires the conversations table.
        # It will run when ConversationStore initializes that table.
        if version == 3:
            table_exists = connection.execute(
                """
                SELECT 1
                FROM sqlite_master
                WHERE type = 'table' AND name = 'conversations'
                """
            ).fetchone()

            if not table_exists:
                continue

        migration(connection)

        connection.execute(
            "INSERT INTO schema_migrations (version) VALUES (?)",
            (version,),
        )