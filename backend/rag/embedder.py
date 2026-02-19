"""Text embedder for the RAG ingestion pipeline.

Embedding providers
-------------------
``ollama`` (default)
    Calls the local Ollama REST API at ``/api/embeddings``.
    Configure via ``OLLAMA_BASE_URL`` and ``OLLAMA_EMBED_MODEL``.

``openai``
    Calls the OpenAI embeddings API.
    Requires ``OPENAI_API_KEY`` to be set.
    Configure via ``OPENAI_EMBED_MODEL``.

Set ``EMBEDDING_PROVIDER=openai`` in your ``.env`` to switch providers.
"""

from __future__ import annotations

import httpx

from backend.config import settings


# ---------------------------------------------------------------------------
# Provider implementations
# ---------------------------------------------------------------------------

def _embed_ollama(text: str) -> list[float]:
    """Call Ollama ``/api/embeddings`` and return the embedding vector."""
    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            f"{settings.ollama_base_url}/api/embeddings",
            json={"model": settings.ollama_embed_model, "prompt": text},
        )
        response.raise_for_status()
        return response.json()["embedding"]


def _embed_openai(text: str) -> list[float]:
    """Call the OpenAI embeddings API and return the embedding vector."""
    import os

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise EnvironmentError(
            "OPENAI_API_KEY environment variable is not set. "
            "Set it or switch to EMBEDDING_PROVIDER=ollama."
        )

    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": settings.openai_embed_model, "input": text},
        )
        response.raise_for_status()
        return response.json()["data"][0]["embedding"]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def embed_text(text: str) -> list[float]:
    """Return an embedding vector for *text*.

    The active provider is determined by ``settings.embedding_provider``
    (``"ollama"`` or ``"openai"``).

    Args:
        text: The input string to embed.  Should be a single chunk (not a
            full document) for best quality.

    Returns:
        A list of floats with length ``settings.embedding_dim``.

    Raises:
        httpx.HTTPStatusError: If the embedding API returns a non-2xx status.
        EnvironmentError: If ``OPENAI_API_KEY`` is missing when using the
            OpenAI provider.
    """
    if settings.embedding_provider == "openai":
        return _embed_openai(text)
    return _embed_ollama(text)
