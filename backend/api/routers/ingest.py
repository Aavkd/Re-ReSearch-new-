"""Ingestion endpoints — URL and PDF.

Routes
------
POST /ingest/url    Body: {"url": "https://..."}    → ingest_url
POST /ingest/pdf    Multipart file upload           → ingest_pdf
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request, UploadFile
from pydantic import BaseModel, HttpUrl

from backend.rag.ingestor import ingest_url
from backend.rag.pdf_ingestor import ingest_pdf

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class UrlIngestRequest(BaseModel):
    url: HttpUrl


class IngestResponse(BaseModel):
    node_id: str
    title: str
    node_type: str
    metadata: dict[str, Any]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ingest_response(node) -> dict[str, Any]:  # type: ignore[type-arg]
    return {
        "node_id": node.id,
        "title": node.title,
        "node_type": node.node_type,
        "metadata": node.metadata,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/url", response_model=IngestResponse, status_code=201)
def ingest_url_endpoint(body: UrlIngestRequest, request: Request) -> dict[str, Any]:
    """Scrape a URL, chunk its text, embed each chunk, and persist to the DB.

    Returns the created ``Source`` node.
    """
    conn = request.app.state.db
    url_str = str(body.url)
    try:
        node = ingest_url(conn, url_str)
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Ingestion failed: {exc}"
        ) from exc
    return _ingest_response(node)


@router.post("/pdf", response_model=IngestResponse, status_code=201)
async def ingest_pdf_endpoint(file: UploadFile, request: Request) -> dict[str, Any]:
    """Upload a PDF file, extract its text, and ingest it into the knowledge base.

    The uploaded file is saved to a temporary location, ingested, then deleted.
    Returns the created ``Source`` node.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=422, detail="Uploaded file must be a PDF.")

    conn = request.app.state.db

    # Write the upload to a named temp file so ingest_pdf can open it
    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = Path(tmp.name)
        content = await file.read()
        tmp.write(content)

    try:
        node = ingest_pdf(conn, tmp_path)
    except Exception as exc:
        raise HTTPException(
            status_code=422, detail=f"PDF ingestion failed: {exc}"
        ) from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    return _ingest_response(node)
