"""FastAPI HTTP layer package.

Public re-export so callers can write::

    from backend.api import app

    uvicorn backend.api:app --reload
"""

from backend.api.app import app

__all__ = ["app"]
