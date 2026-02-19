"""Centralised settings for the Re:Search backend.

All runtime configuration is resolved here in one place.  Values can be
overridden via environment variables or a `.env` file in the project root
(loaded automatically when this module is imported).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root (two levels up from this file)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path, override=False)


@dataclass
class Settings:
    # ------------------------------------------------------------------
    # Workspace / storage
    # ------------------------------------------------------------------
    workspace_dir: Path = field(
        default_factory=lambda: Path(
            os.environ.get("RESEARCH_WORKSPACE", Path.home() / ".research_data")
        )
    )

    @property
    def db_path(self) -> Path:
        """Absolute path to the SQLite database file."""
        return self.workspace_dir / "library.db"

    @property
    def schema_path(self) -> Path:
        """Absolute path to the schema SQL file bundled with the package."""
        return Path(__file__).resolve().parent / "db" / "schema.sql"

    # ------------------------------------------------------------------
    # Embedding model
    # ------------------------------------------------------------------
    embedding_provider: str = field(
        default_factory=lambda: os.environ.get("EMBEDDING_PROVIDER", "ollama")
    )
    ollama_base_url: str = field(
        default_factory=lambda: os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    )
    ollama_embed_model: str = field(
        default_factory=lambda: os.environ.get("OLLAMA_EMBED_MODEL", "embeddinggemma:latest")
    )
    openai_embed_model: str = field(
        default_factory=lambda: os.environ.get(
            "OPENAI_EMBED_MODEL", "text-embedding-3-small"
        )
    )
    embedding_dim: int = field(
        default_factory=lambda: int(os.environ.get("EMBEDDING_DIM", "768"))
    )

    # ------------------------------------------------------------------
    # Chat / reasoning model
    # ------------------------------------------------------------------
    llm_provider: str = field(
        default_factory=lambda: os.environ.get("LLM_PROVIDER", "ollama")
    )
    ollama_chat_model: str = field(
        default_factory=lambda: os.environ.get("OLLAMA_CHAT_MODEL", "ministral-3:8b")
    )
    openai_chat_model: str = field(
        default_factory=lambda: os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    )

    # ------------------------------------------------------------------
    # Scraper
    # ------------------------------------------------------------------
    rate_limit_delay: float = field(
        default_factory=lambda: float(os.environ.get("RATE_LIMIT_DELAY", "1.0"))
    )
    request_timeout: float = field(
        default_factory=lambda: float(os.environ.get("REQUEST_TIMEOUT", "30.0"))
    )

    # ------------------------------------------------------------------
    # RAG chunking
    # ------------------------------------------------------------------
    chunk_size: int = field(
        default_factory=lambda: int(os.environ.get("CHUNK_SIZE", "512"))
    )
    chunk_overlap: int = field(
        default_factory=lambda: int(os.environ.get("CHUNK_OVERLAP", "64"))
    )

    # ------------------------------------------------------------------
    # Agent
    # ------------------------------------------------------------------
    agent_max_iterations: int = field(
        default_factory=lambda: int(os.environ.get("AGENT_MAX_ITERATIONS", "5"))
    )
    agent_max_concurrent_scrapes: int = field(
        default_factory=lambda: int(os.environ.get("AGENT_MAX_CONCURRENT_SCRAPES", "3"))
    )

    def ensure_workspace(self) -> None:
        """Create the workspace directory if it does not exist."""
        self.workspace_dir.mkdir(parents=True, exist_ok=True)


# Module-level singleton — import this everywhere:
#   from backend.config import settings
settings = Settings()
