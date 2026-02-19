"""Research agent endpoint with Server-Sent Events (SSE) streaming.

Routes
------
POST /research    Body: {"goal": "...", "depth": "quick|deep"}

The endpoint streams progress as SSE events while the LangGraph agent runs
in a background thread.  Each graph-node transition is emitted as a separate
SSE event so the client can render a live "Agent HUD".  A final ``done``
event carries the complete report.

SSE event format
----------------
Each event is a JSON-encoded object on the ``data:`` line::

    data: {"event": "node", "node": "planner", "status": "planning", ...}

    data: {"event": "done", "report": "...", "artifact_id": "..."}

    data: {"event": "error", "detail": "..."}
"""

from __future__ import annotations

import asyncio
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, AsyncIterator, Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.agent.graph import build_graph
from backend.agent.state import ResearchState
from backend.config import settings
from backend.db import get_connection, init_db
from backend.db.nodes import create_node

router = APIRouter()

# Shared thread pool — research runs are CPU/IO bound but the thread limit
# keeps excessive parallelism in check.
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="research")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ResearchRequest(BaseModel):
    goal: str
    # depth is accepted for API compatibility; reserved for future use.
    depth: Optional[str] = None


# ---------------------------------------------------------------------------
# SSE helpers
# ---------------------------------------------------------------------------

def _sse(payload: dict[str, Any]) -> str:
    """Format a payload dict as a single SSE ``data:`` line."""
    return f"data: {json.dumps(payload)}\n\n"


# ---------------------------------------------------------------------------
# Background runner
# ---------------------------------------------------------------------------

def _run_graph(
    goal: str,
    queue: "asyncio.Queue[str | None]",
    loop: asyncio.AbstractEventLoop,
) -> None:
    """Execute the research graph and push SSE-formatted strings into *queue*.

    Runs in a ThreadPoolExecutor.  Uses ``loop.call_soon_threadsafe`` to
    communicate back to the async event loop without blocking it.

    A ``None`` sentinel is enqueued when the thread finishes (success or
    error) so the async generator knows to stop.
    """
    def _put(payload: dict[str, Any]) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, _sse(payload))

    conn = get_connection()
    init_db(conn)
    try:
        settings.ensure_workspace()
        graph = build_graph(conn)

        thread_id = str(uuid.uuid4())
        run_config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}

        initial_state: ResearchState = {
            "goal": goal,
            "plan": [],
            "urls_found": [],
            "urls_scraped": [],
            "findings": [],
            "report": "",
            "iteration": 0,
            "status": "planning",
        }

        # Stream node-by-node transitions
        for event in graph.stream(initial_state, config=run_config):
            node_name = next(iter(event), None)
            if node_name:
                update: dict[str, Any] = event[node_name]
                _put(
                    {
                        "event": "node",
                        "node": node_name,
                        "status": update.get("status", ""),
                        "iteration": update.get("iteration", 0),
                        "urls_scraped": update.get("urls_scraped", []),
                        "findings_count": len(update.get("findings", [])),
                    }
                )

        # Retrieve final accumulated state
        final: ResearchState = graph.get_state(run_config).values  # type: ignore[assignment]
        report_text = final.get("report", "")

        artifact_id: Optional[str] = None
        if report_text:
            artifact = create_node(
                conn,
                title=f"Report: {goal[:80]}",
                node_type="Artifact",
                metadata={
                    "goal": goal,
                    "iterations": final.get("iteration", 0),
                    "sources_count": len(final.get("urls_scraped", [])),
                },
            )
            artifact_id = artifact.id

        _put(
            {
                "event": "done",
                "report": report_text,
                "artifact_id": artifact_id,
                "iterations": final.get("iteration", 0),
                "sources_scraped": final.get("urls_scraped", []),
            }
        )

    except Exception as exc:  # noqa: BLE001
        _put({"event": "error", "detail": str(exc)})

    finally:
        conn.close()
        loop.call_soon_threadsafe(queue.put_nowait, None)  # sentinel


# ---------------------------------------------------------------------------
# Async SSE generator
# ---------------------------------------------------------------------------

async def _research_sse_generator(goal: str) -> AsyncIterator[str]:
    """Yield SSE-formatted strings for the duration of a research run."""
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue[str | None] = asyncio.Queue()

    future = loop.run_in_executor(_executor, _run_graph, goal, queue, loop)

    try:
        while True:
            item = await queue.get()
            if item is None:
                break
            yield item
    finally:
        # Ensure the background thread future is awaited to surface exceptions
        try:
            await asyncio.shield(future)
        except Exception:  # noqa: BLE001
            pass


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@router.post("")
async def research(body: ResearchRequest) -> StreamingResponse:
    """Run the autonomous research agent and stream progress as SSE.

    The response is a ``text/event-stream`` where each ``data:`` line is a
    JSON object with an ``event`` field:

    - ``node``  — emitted after each graph node completes.
    - ``done``  — emitted at the end with the full report and artifact UUID.
    - ``error`` — emitted if the agent raises an unhandled exception.
    """
    return StreamingResponse(
        _research_sse_generator(body.goal),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disable nginx proxy buffering
        },
    )
