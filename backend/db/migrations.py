"""Database initialisation and migration helpers.

``init_db(conn)`` is idempotent — safe to call on an existing database.
``migrate(conn)`` runs incremental schema changes tracked in a version table.
"""

from __future__ import annotations

import sqlite3

from backend.config import settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_schema() -> str:
    """Load schema.sql and inject runtime values (e.g. embedding dimension)."""
    schema_path = settings.schema_path
    template = schema_path.read_text(encoding="utf-8")
    return template.replace("{embedding_dim}", str(settings.embedding_dim))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def init_db(conn: sqlite3.Connection) -> None:
    """Create all tables, indexes, triggers, and virtual tables.

    This function is **idempotent**: every DDL statement uses ``IF NOT EXISTS``
    so calling it multiple times on the same database is safe.

    Args:
        conn: An open, configured SQLite connection (sqlite-vec already loaded).
    """
    sql = _read_schema()
    # executescript() handles compound statements (BEGIN…END in triggers) and
    # knows how to split a multi-statement script correctly.  It issues an
    # implicit COMMIT before execution, which is fine for DDL-only scripts.
    conn.executescript(sql)
    _ensure_version_table(conn)


def _ensure_version_table(conn: sqlite3.Connection) -> None:
    """Create the internal schema-version tracking table if absent."""
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_version (
                version  INTEGER PRIMARY KEY,
                applied_at INTEGER DEFAULT (unixepoch())
            )
            """
        )


def current_version(conn: sqlite3.Connection) -> int:
    """Return the highest applied migration version (0 if none applied)."""
    row = conn.execute(
        "SELECT COALESCE(MAX(version), 0) FROM schema_version"
    ).fetchone()
    return row[0] if row else 0


def migrate(conn: sqlite3.Connection) -> None:
    """Run any pending incremental migrations.

    Each migration is a tuple of ``(version: int, sql: str)``.  Migrations are
    applied in version order and recorded in ``schema_version``.

    Add future migrations to the ``MIGRATIONS`` list below.
    """
    MIGRATIONS: list[tuple[int, str]] = [
        # (1, "ALTER TABLE nodes ADD COLUMN foo TEXT;"),
    ]

    applied = current_version(conn)
    for version, sql in MIGRATIONS:
        if version > applied:
            with conn:
                conn.execute(sql)
                conn.execute(
                    "INSERT INTO schema_version(version) VALUES (?)", (version,)
                )
