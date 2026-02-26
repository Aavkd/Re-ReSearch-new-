"""Database layer package.

Public re-exports so callers can write::

    from backend.db import get_connection, init_db
    from backend.db import chat
"""

from backend.db.connection import get_connection
from backend.db.migrations import init_db
from backend.db import chat

__all__ = ["get_connection", "init_db", "chat"]
