"""LangGraph node functions for the research agent.

Each public symbol is a *factory* that accepts an open DB connection and
returns a callable ``(ResearchState) -> dict`` suitable for use as a
LangGraph node.  Using factories (closures) keeps the connection out of the
state bag while still allowing node functions to access the DB.

Public factories
----------------
``make_planner``     — decomposes the goal into search queries via LLM.
``make_searcher``    — runs DuckDuckGo searches for each query.
``make_scraper``     — scrapes and ingests URLs from the searcher.
``make_synthesiser`` — writes the final report via LLM.
``make_evaluator``   — decides whether to loop or terminate.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from backend.agent.state import ResearchState
from backend.agent.tools import rag_retrieve, scrape_and_ingest, web_search
from backend.config import settings


# ---------------------------------------------------------------------------
# LLM helper
# ---------------------------------------------------------------------------

def _get_llm() -> Any:
    """Return a configured LangChain chat model based on ``settings``.

    Reads ``settings.llm_provider`` (``"ollama"`` or ``"openai"``) and
    instantiates the matching LangChain integration with ``temperature=0``
    for deterministic output.
    """
    if settings.llm_provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=settings.openai_chat_model, temperature=0)

    from langchain_ollama import ChatOllama

    return ChatOllama(model=settings.ollama_chat_model, temperature=0)


# ---------------------------------------------------------------------------
# Node factories
# ---------------------------------------------------------------------------

def make_planner(conn: sqlite3.Connection):
    """Return a *planner* node function.

    The planner calls the LLM to decompose the research goal into a short
    list of concrete search queries, then increments the iteration counter.
    """

    def planner(state: ResearchState) -> dict:
        print(f"[PLANNING] Decomposing goal: {state['goal']!r} …")
        llm = _get_llm()
        prompt = (
            "You are a research assistant helping gather information on a topic.\n"
            "Given the research goal below, generate exactly 3 specific, concise "
            "search queries (one per line, no numbering, no bullets, no extra text) "
            "that will help collect diverse and relevant sources.\n\n"
            f"Goal: {state['goal']}\n\n"
            "Search queries:"
        )
        response = llm.invoke(prompt)
        raw = response.content if hasattr(response, "content") else str(response)
        queries = [q.strip() for q in raw.splitlines() if q.strip()][:3]
        if not queries:
            queries = [state["goal"]]
        print(f"[PLANNING] Generated {len(queries)} queries: {queries}")
        return {
            "plan": queries,
            "iteration": state.get("iteration", 0) + 1,
            "status": "searching",
        }

    return planner


def make_searcher(conn: sqlite3.Connection):
    """Return a *searcher* node function.

    The searcher runs a DuckDuckGo search for each query in the plan,
    collecting and deduplicating the result URLs.
    """

    def searcher(state: ResearchState) -> dict:
        urls: list[str] = []
        for query in state.get("plan", []):
            print(f"[SEARCHING] Query: {query!r}")
            try:
                found = web_search(query)
                print(f"[SEARCHING] Found {len(found)} URL(s).")
                urls.extend(found)
            except Exception as exc:
                print(f"[SEARCHING] web_search failed for {query!r}: {exc}")

        # Deduplicate while preserving insertion order.
        seen: set[str] = set()
        unique: list[str] = []
        for u in urls:
            if u not in seen:
                seen.add(u)
                unique.append(u)

        print(f"[SEARCHING] {len(unique)} unique URL(s) queued for scraping.")
        return {"urls_found": unique, "status": "scraping"}

    return searcher


def make_scraper(conn: sqlite3.Connection):
    """Return a *scraper* node function.

    The scraper ingests up to ``settings.agent_max_concurrent_scrapes`` new
    URLs (those not already in ``urls_scraped``).  Failures are logged and
    skipped rather than aborting the pipeline.
    """

    def scraper(state: ResearchState) -> dict:
        already_scraped: list[str] = list(state.get("urls_scraped", []))
        findings: list[str] = list(state.get("findings", []))
        limit = settings.agent_max_concurrent_scrapes

        new_urls = [u for u in state.get("urls_found", []) if u not in already_scraped]
        for url in new_urls[:limit]:
            print(f"[SCRAPING] {url}")
            try:
                summary = scrape_and_ingest(conn, url)
                already_scraped.append(url)
                findings.append(summary)
                print(f"[SCRAPING] ✓ {summary}")
            except Exception as exc:
                print(f"[SCRAPING] ✗ Failed {url!r}: {exc}")

        return {
            "urls_scraped": already_scraped,
            "findings": findings,
            "status": "synthesising",
        }

    return scraper


def make_synthesiser(conn: sqlite3.Connection):
    """Return a *synthesiser* node function.

    The synthesiser first retrieves relevant chunks from the knowledge base
    (using the goal as a query), then calls the LLM to write a structured
    report from the ingested findings and the retrieved context.
    """

    def synthesiser(state: ResearchState) -> dict:
        print("[SYNTHESISING] Retrieving relevant context …")
        context = rag_retrieve(conn, state["goal"])

        findings_text = "\n".join(state.get("findings", [])) or "(no sources ingested)"

        print("[SYNTHESISING] Writing report …")
        llm = _get_llm()
        prompt = (
            "You are a research analyst tasked with writing a comprehensive report.\n\n"
            f"Research Goal: {state['goal']}\n\n"
            f"Sources ingested:\n{findings_text}\n\n"
            f"Relevant excerpts from the knowledge base:\n{context}\n\n"
            "Write a well-structured, informative report in markdown format. "
            "Include an introduction, key findings, and a conclusion."
        )
        response = llm.invoke(prompt)
        report = response.content if hasattr(response, "content") else str(response)
        print(f"[SYNTHESISING] Report written ({len(report)} chars).")
        return {"report": report, "status": "evaluating"}

    return synthesiser


def make_evaluator(conn: sqlite3.Connection):
    """Return an *evaluator* node function.

    The evaluator decides whether the research is complete:

    * If any findings were collected **or** the iteration limit has been
      reached → ``status = "done"``.
    * Otherwise → ``status = "re-planning"`` to trigger another loop.
    """

    def evaluator(state: ResearchState) -> dict:
        iteration = state.get("iteration", 1)
        has_findings = bool(state.get("findings"))
        at_limit = iteration >= settings.agent_max_iterations

        if has_findings or at_limit:
            if at_limit and not has_findings:
                print(
                    f"[EVALUATING] Iteration limit ({settings.agent_max_iterations}) "
                    "reached with no findings.  Terminating."
                )
            else:
                print(
                    f"[EVALUATING] Research complete after {iteration} iteration(s)."
                )
            return {"status": "done"}

        print(
            f"[EVALUATING] No findings yet (iteration {iteration}); "
            "re-planning …"
        )
        return {"status": "re-planning"}

    return evaluator
