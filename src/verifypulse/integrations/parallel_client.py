"""
Parallel Web API client.

Small wrapper around the Parallel web search API so the workflow can
pull live context (docs, examples, best practices) for any requirement.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx


class ParallelClient:
    """
    Minimal Parallel Web client.

    We only need a single call for the hackathon:
    - search_web: given a query, return a short summarized snippet.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.parallelai.xyz",
        timeout: float = 15.0,
    ) -> None:
        self.api_key = api_key or os.getenv("PARALLEL_API_KEY", "")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        if not self.api_key:
            # Fail soft: we never crash the pipeline if key is missing.
            # The workflow will see `enabled=False` and skip web search.
            self.enabled = False
        else:
            self.enabled = True

    def _client(self) -> httpx.Client:
        """Create an HTTP client with auth header."""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        return httpx.Client(base_url=self.base_url, headers=headers, timeout=self.timeout)

    def search_web(self, query: str, max_tokens: int = 256) -> Dict[str, Any]:
        """
        Call Parallel web search for the given query.

        Returns a small dict we can safely log + send back to the user.
        In case of any error, we swallow it and return a fallback.
        """
        if not self.enabled:
            return {
                "enabled": False,
                "reason": "Parallel API key missing",
                "query": query,
            }

        payload = {
            "query": query,
            "max_tokens": max_tokens,
        }

        try:
            with self._client() as client:
                # NOTE: endpoint name may differ slightly depending on docs.
                # This is intentionally simple; adjust path if needed.
                resp = client.post("/v1/web/search", json=payload)
                resp.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            return {
                "enabled": False,
                "reason": f"Parallel request failed: {exc!s}",
                "query": query,
            }

        data: Dict[str, Any] = resp.json()

        # Normalize into a compact dict for the workflow.
        return {
            "enabled": True,
            "query": query,
            "raw": data,
        }

    def search_security_guidelines(self, requirement: str) -> dict:
        """
        Backwards-compatible helper for the planner.

        Uses search_web() to fetch security best practices for the requirement.
        """
        query = f"{requirement} API security guidelines best practices login authentication"
        return self.search_web(query)

    def search_login_checklist(self, requirement: str) -> dict:
        """
        Backwards-compatible helper for the planner.

        Uses search_web() to fetch a checklist of test ideas / cases.
        """
        query = f"{requirement} API login validation checklist test cases"
        return self.search_web(query)
