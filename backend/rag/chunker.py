"""Text chunker for the RAG ingestion pipeline.

Strategy: recursive character splitting on ``\\n\\n`` → ``\\n`` → ``" "``,
then merge small pieces into overlapping chunks of at most *chunk_size*
characters.  The overlap seeds each new chunk with the tail of the previous
one to preserve context across boundaries.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _recursive_split(text: str, separators: list[str], chunk_size: int) -> list[str]:
    """Split *text* into pieces that are each at most *chunk_size* characters.

    Tries separators in order.  If no separator breaks the text into pieces
    small enough, falls back to a hard character-boundary cut.
    """
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    for idx, sep in enumerate(separators):
        if sep in text:
            remaining_seps = separators[idx + 1 :]
            raw_parts = text.split(sep)
            result: list[str] = []
            for part in raw_parts:
                stripped = part.strip()
                if not stripped:
                    continue
                if len(stripped) <= chunk_size:
                    result.append(stripped)
                else:
                    result.extend(_recursive_split(stripped, remaining_seps, chunk_size))
            return result

    # No separator found (e.g. a single very long word): hard cut.
    return [
        text[i : i + chunk_size]
        for i in range(0, len(text), chunk_size)
        if text[i : i + chunk_size].strip()
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def chunk_text(
    text: str,
    chunk_size: int = 512,
    overlap: int = 64,
) -> list[str]:
    """Split *text* into overlapping, size-bounded chunks.

    Args:
        text: The raw text to chunk.
        chunk_size: Maximum number of **characters** per chunk.
        overlap: How many characters from the end of the previous chunk to
            prepend to the next one (preserves sentence context).

    Returns:
        A list of non-empty string chunks.  Returns ``[]`` for blank input.

    Algorithm:
        1. Recursively split on ``\\n\\n`` → ``\\n`` → ``" "`` until every
           piece fits within *chunk_size*.
        2. Greedily merge pieces into a buffer.  When the next piece would
           overflow the buffer, emit the buffer as a chunk, then seed the
           new buffer with the tail *overlap* characters of the emitted chunk
           (trimmed to the nearest word boundary).
    """
    if not text.strip():
        return []

    pieces = _recursive_split(text.strip(), ["\n\n", "\n", " "], chunk_size)

    chunks: list[str] = []
    buf: list[str] = []

    for piece in pieces:
        tentative = " ".join(buf + [piece]) if buf else piece
        if len(tentative) > chunk_size and buf:
            # Emit the current buffer.
            chunk = " ".join(buf)
            chunks.append(chunk)

            # Seed the next buffer with an overlap tail.
            if len(chunk) > overlap:
                cut = len(chunk) - overlap
                # Advance to the next word boundary so we don't start mid-word.
                space_idx = chunk.find(" ", cut)
                overlap_text = chunk[space_idx + 1 :] if space_idx != -1 else chunk[cut:]
            else:
                overlap_text = chunk

            buf = [overlap_text] if overlap_text.strip() else []

        buf.append(piece)

    if buf:
        chunks.append(" ".join(buf))

    return [c for c in chunks if c.strip()]
