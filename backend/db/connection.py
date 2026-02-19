"""SQLite connection factory.

Usage::

    from backend.db.connection import get_connection

    with get_connection() as conn:
        cursor = conn.execute("SELECT 1")
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

import sqlite_vec

from backend.config import settings


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Open and configure a SQLite connection.

    Steps performed on every new connection:
    1. Load the ``sqlite-vec`` extension (vector search).
    2. Enable ``PRAGMA foreign_keys = ON``.
    3. Switch to WAL journal mode for concurrent readers.

    Args:
        db_path: Override the DB path.  Defaults to ``settings.db_path``.

    Returns:
        A configured :class:`sqlite3.Connection` with ``row_factory`` set to
        :class:`sqlite3.Row` so columns can be accessed by name.
    """
    path = db_path or settings.db_path

    # Create parent directory if needed (no-op for `:memory:`)
    if str(path) != ":memory:":
        settings.ensure_workspace()

    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # Load sqlite-vec extension.
    # enable_load_extension must be called before any load attempt;
    # it is immediately disabled again after loading for security.
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)

    # PRAGMAs
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")

    return conn
