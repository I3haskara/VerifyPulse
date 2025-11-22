"""
Agentic AI Quality Coach
========================
End-to-end pipeline for API testing, RAG-based context retrieval,
and automated failure analysis with LLM-powered diagnostics.
"""

__version__ = "0.1.0"

from .agent_runner import run_agent

__all__ = ["run_agent"]
