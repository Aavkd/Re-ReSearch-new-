"""Project-scoped chat endpoints with SSE streaming.

Routes
------
GET    /projects/{project_id}/chat                       List all conversations
POST   /projects/{project_id}/chat                       Create a new (empty) conversation
GET    /projects/{project_id}/chat/{conv_id}             Fetch conversation + full message history
POST   /projects/{project_id}/chat/{conv_id}/messages    Send a message (SSE token stream)
DELETE /projects/{project_id}/chat/{conv_id}             Delete a conversation

Note: this router is mounted with prefix ``/projects`` in ``app.py``,
so its path definitions start with ``/{project_id}/chat``.
"""

from __future__ import annotations

import json
from time import time
from typing import Any, AsyncIterator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

from backend.db import chat as chat_db
from backend.db.nodes import get_node
from backend.rag.chat import chat_stream

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class NewConversationRequest(BaseModel):
    title: str = "New conversation"


class ChatMessageRequest(BaseModel):
    message: str
    history: list[dict[str, Any]] = []


class ChatConversationOut(BaseModel):
    id: str
    title: str
    messages: list[dict[str, Any]]
    created_at: int
    updated_at: int


# ---------------------------------------------------------------------------
# Serialisation helper
# ---------------------------------------------------------------------------

def _conv_out(node: Any) -> ChatConversationOut:
    return ChatConversationOut(
        id=node.id,
        title=node.title,
        messages=node.metadata.get("messages", []),
        created_at=node.created_at,
        updated_at=node.updated_at,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/{project_id}/chat", response_model=list[ChatConversationOut])
def list_conversations_endpoint(
    project_id: str,
    request: Request,
) -> list[ChatConversationOut]:
    """List all conversations for a project, ordered by most recently active."""
    conn = request.app.state.db
    if get_node(conn, project_id) is None:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")
    convs = chat_db.list_conversations(conn, project_id)
    return [_conv_out(c) for c in convs]


@router.post("/{project_id}/chat", status_code=201, response_model=ChatConversationOut)
def create_conversation_endpoint(
    project_id: str,
    body: NewConversationRequest,
    request: Request,
) -> ChatConversationOut:
    """Create a new empty conversation linked to the project."""
    conn = request.app.state.db
    if get_node(conn, project_id) is None:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")
    conv = chat_db.create_conversation(conn, project_id, title=body.title)
    return _conv_out(conv)


@router.get("/{project_id}/chat/{conv_id}", response_model=ChatConversationOut)
def get_conversation_endpoint(
    project_id: str,
    conv_id: str,
    request: Request,
) -> ChatConversationOut:
    """Fetch a conversation with its full message history."""
    conn = request.app.state.db
    if get_node(conn, project_id) is None:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")
    conv = chat_db.get_conversation(conn, conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail=f"Conversation '{conv_id}' not found.")
    return _conv_out(conv)


@router.delete("/{project_id}/chat/{conv_id}", status_code=204, response_class=Response, response_model=None)
def delete_conversation_endpoint(
    project_id: str,
    conv_id: str,
    request: Request,
) -> Response:
    """Delete a conversation and all its messages."""
    conn = request.app.state.db
    if get_node(conn, project_id) is None:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")
    conv = chat_db.get_conversation(conn, conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail=f"Conversation '{conv_id}' not found.")
    chat_db.delete_conversation(conn, conv_id)
    return Response(status_code=204)


@router.post("/{project_id}/chat/{conv_id}/messages")
async def send_message_endpoint(
    project_id: str,
    conv_id: str,
    body: ChatMessageRequest,
    request: Request,
) -> StreamingResponse:
    """Send a user message and stream back the assistant reply as SSE.

    SSE event shapes::

        data: {"event": "token",    "text": " ..."}
        data: {"event": "citation", "nodes": [{"id":"...", "title":"...", "url":"..."}]}
        data: {"event": "done"}
        data: {"event": "error",    "detail": "..."}
    """
    conn = request.app.state.db

    if get_node(conn, project_id) is None:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")

    conv = chat_db.get_conversation(conn, conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail=f"Conversation '{conv_id}' not found.")

    # Persist user message immediately before streaming starts
    user_msg: dict[str, Any] = {
        "role": "user",
        "content": body.message,
        "ts": int(time()),
    }
    chat_db.append_messages(conn, conv_id, [user_msg])

    return StreamingResponse(
        _chat_sse_generator(conn, project_id, conv_id, body.message, body.history),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# SSE generator
# ---------------------------------------------------------------------------

async def _chat_sse_generator(
    conn: Any,
    project_id: str,
    conv_id: str,
    question: str,
    history: list[dict[str, Any]],
) -> AsyncIterator[str]:
    """Wrap ``chat_stream``, forward every SSE frame, and persist the reply."""
    accumulated_tokens: list[str] = []

    try:
        async for frame in chat_stream(
            conn=conn,
            question=question,
            history=history,
            project_id=project_id,
        ):
            # frame is already an SSE-formatted string: "data: {...}\n\n"
            yield frame

            # Parse only to accumulate token text for persistence
            try:
                payload = json.loads(frame.removeprefix("data: ").strip())
                if payload.get("event") == "token":
                    accumulated_tokens.append(payload.get("text", ""))
                elif payload.get("event") == "done":
                    # Persist the complete assistant message
                    full_reply = "".join(accumulated_tokens)
                    if full_reply:
                        assistant_msg: dict[str, Any] = {
                            "role": "assistant",
                            "content": full_reply,
                            "ts": int(time()),
                        }
                        chat_db.append_messages(conn, conv_id, [assistant_msg])
            except (json.JSONDecodeError, AttributeError):
                pass

    except Exception as exc:  # noqa: BLE001
        error_frame = f"data: {json.dumps({'event': 'error', 'detail': str(exc)})}\n\n"
        yield error_frame
