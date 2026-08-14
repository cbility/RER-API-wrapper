from __future__ import annotations

import os
from typing import Any

import requests

from rer_scraper.models import ScraperOperations


class SmartSuiteClient:
    """Owns SmartSuite HTTP access and scraper-specific record mappings."""

    def __init__(
        self,
        api_url: str | None,
        api_token: str | None,
        account_id: str | None,
        timeout: int = 30,
    ):
        self.api_url = (api_url or "https://app.smartsuite.com/api/v1").rstrip("/")
        self.api_token = api_token
        self.account_id = account_id
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Token {api_token}" if api_token else "",
                "ACCOUNT-ID": account_id or "",
                "Content-Type": "application/json",
            }
        )

    @classmethod
    def from_env(cls) -> "SmartSuiteClient":
        return cls(
            api_url=os.getenv("SMARTSUITE_API_URL"),
            api_token=os.getenv("SMARTSUITE_API_TOKEN"),
            account_id=os.getenv("SMARTSUITE_ACCOUNT_ID"),
            timeout=int(os.getenv("SMARTSUITE_TIMEOUT_SECONDS", "30")),
        )

    def get_operations(self) -> ScraperOperations:
        """Return pending scraper work once the SmartSuite schema is configured."""
        return ScraperOperations()

    def _get_record(self, table_id: str, record_id: str) -> dict[str, Any]:
        response = self.session.get(self._record_url(table_id, record_id), timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def _create_record(self, table_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        response = self.session.post(self._records_url(table_id), json=fields, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def _update_record(self, table_id: str, record_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        response = self.session.patch(self._record_url(table_id, record_id), json=fields, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def _records_url(self, table_id: str) -> str:
        self._validate_configuration()
        return f"{self.api_url}/applications/{table_id}/records/"

    def _record_url(self, table_id: str, record_id: str) -> str:
        return f"{self._records_url(table_id)}{record_id}/"

    def _validate_configuration(self) -> None:
        missing = []
        if not self.api_token:
            missing.append("SMARTSUITE_API_TOKEN")
        if not self.account_id:
            missing.append("SMARTSUITE_ACCOUNT_ID")
        if missing:
            raise RuntimeError(f"Missing SmartSuite configuration: {', '.join(missing)}")
