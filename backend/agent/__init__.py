"""LangGraph researcher agent package.

Public API::

    from backend.agent import run_research
    state = run_research("What is solid-state battery technology?")
"""

from backend.agent.runner import run_research

__all__ = ["run_research"]
