"""
Skyflow integration client for VerifyPulse.

Responsibilities
- Read config from environment (vault ID, API token, base URL)
- Provide a single public helper: tokenize_record(record: dict) -> dict
- Fail soft: if disabled or any error occurs, return the original record
  and mark enabled = False in the response.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import httpx


DEFAULT_SKYFLOW_BASE_URL = "https://prod.skyflowapis.com/v1"


class SkyflowClient:
    """Thin wrapper around the Skyflow tokenization API.

    Usage:
        client = SkyflowClient()
        result = client.tokenize_record({"ssn": "123-45-6789"})
    """

    def __init__(
        self,
        vault_id: Optional[str] = None,
        api_token: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 10.0,
        enabled: Optional[bool] = None,
    ) -> None:
        # Read configuration from environment if not provided explicitly
        env_vault_id = os.getenv("SKYFLOW_VAULT_ID")
        env_token = os.getenv("SKYFLOW_API_TOKEN")
        env_base_url = os.getenv("SKYFLOW_BASE_URL", DEFAULT_SKYFLOW_BASE_URL)

        self.vault_id: Optional[str] = vault_id or env_vault_id
        self.api_token: Optional[str] = api_token or env_token
        self.base_url: str = base_url or env_base_url
        self.timeout: float = timeout

        # Enabled only if we have the minimum required config
        if enabled is None:
            self.enabled: bool = bool(self.vault_id and self.api_token)
        else:
            self.enabled = enabled and bool(self.vault_id and self.api_token)

    # --------------------------------------------------------------------- #
    # Internal helpers
    # --------------------------------------------------------------------- #

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    def _tokenize_endpoint(self) -> str:
        # Example: https://prod.skyflowapis.com/v1/vaults/{vault_id}/tokenize
        return f"{self.base_url}/vaults/{self.vault_id}/tokenize"

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #

    def tokenize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Tokenize a single record dictionary.

        Returns a normalized dict:

            {
                "enabled": bool,          # whether Skyflow was actually used
                "original": {...},        # the original record
                "tokenized": {...},       # tokenized fields OR original on failure
            }

        Any exception or non-2xx response will fall back to returning the
        original record and marking enabled=False.
        """
        # If configuration is missing, do not attempt to call the API.
        if not self.enabled:
            return {
                "enabled": False,
                "original": record,
                "tokenized": record,
            }

        try:
            payload = {
                "records": [
                    {
                        "fields": record,
                    }
                ]
            }

            response = httpx.post(
                self._tokenize_endpoint(),
                headers=self._headers(),
                json=payload,
                timeout=self.timeout,
            )

            if response.status_code // 100 != 2:
                # Log-friendly message but fail soft.
                print(
                    f"[Skyflow] Tokenization failed with status "
                    f"{response.status_code}: {response.text}"
                )
                return {
                    "enabled": False,
                    "original": record,
                    "tokenized": record,
                }

            data = response.json()
            tokenized_fields: Dict[str, Any] = (
                data.get("records", [{}])[0].get("fields", {}) or record
            )

            return {
                "enabled": True,
                "original": record,
                "tokenized": tokenized_fields,
            }

        except Exception as exc:  # noqa: BLE001
            # Never crash the pipeline because of Skyflow;
            # just fall back gracefully.
            print(f"[Skyflow] Exception during tokenization: {exc!r}")
            return {
                "enabled": False,
                "original": record,
                "tokenized": record,
            }


# ------------------------------------------------------------------------- #
# Module-level helpers used by the rest of the codebase
# ------------------------------------------------------------------------- #

_skyflow_client: Optional[SkyflowClient] = None


def get_skyflow_client() -> SkyflowClient:
    global _skyflow_client
    if _skyflow_client is None:
        _skyflow_client = SkyflowClient()
    return _skyflow_client


def tokenize_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience wrapper so other modules can just call:

        from verifypulse.integrations.skyflow_client import tokenize_record

    """
    client = get_skyflow_client()
    return client.tokenize_record(record)
