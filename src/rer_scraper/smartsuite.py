from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Any, Literal, Sequence

import requests

from rer_scraper.models import ScraperOperations


FilterOperator = Literal["and", "or"]
SortDirection = Literal["asc", "desc"]
MAX_BULK_RECORDS = 25
MAX_LIST_RECORDS = 1000


@dataclass(frozen=True)
class SmartSuiteFilter:
    field: str
    comparison: str
    value: Any


@dataclass(frozen=True)
class SmartSuiteFilterGroup:
    operator: FilterOperator
    fields: Sequence[SmartSuiteFilter]

    def to_payload(self) -> dict[str, Any]:
        return {
            "operator": self.operator,
            "fields": [asdict(filter_) for filter_ in self.fields],
        }


@dataclass(frozen=True)
class SmartSuiteSort:
    field: str
    direction: SortDirection = "asc"


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

    def _list_records(
        self,
        table_id: str,
        filter_group: SmartSuiteFilterGroup | None = None,
        sorts: Sequence[SmartSuiteSort] = (),
        hydrated: bool = False,
        include_deleted: bool = False,
        page_size: int = 1000,
    ) -> list[dict[str, Any]]:
        if not 1 <= page_size <= MAX_LIST_RECORDS:
            raise ValueError(f"page_size must be between 1 and {MAX_LIST_RECORDS}.")

        items: list[dict[str, Any]] = []
        offset = 0
        while True:
            params = {
                "offset": str(offset),
                "limit": str(page_size),
                "all": str(include_deleted).lower(),
            }
            response = self.session.post(
                self._list_records_url(table_id),
                params=params,
                json={
                    "filter": filter_group.to_payload() if filter_group else {},
                    "sort": [asdict(sort) for sort in sorts],
                    "hydrated": hydrated,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
            page_items = payload.get("items", [])
            if not isinstance(page_items, list):
                raise ValueError("SmartSuite list records response did not contain an items list.")
            items.extend(page_items)

            total = payload.get("total")
            if not page_items or (isinstance(total, int) and len(items) >= total):
                break
            offset += len(page_items)
        return items

    def _bulk_add_records(self, table_id: str, records: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        return self._bulk_write_records(table_id, records, method="post", require_ids=False)

    def _bulk_update_records(self, table_id: str, records: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        if any(not record.get("id") for record in records):
            raise ValueError("Each bulk update record must include an id.")
        return self._bulk_write_records(table_id, records, method="patch", require_ids=True)

    def _bulk_write_records(
        self,
        table_id: str,
        records: Sequence[dict[str, Any]],
        method: Literal["post", "patch"],
        require_ids: bool,
    ) -> list[dict[str, Any]]:
        del require_ids
        created_or_updated: list[dict[str, Any]] = []
        for start in range(0, len(records), MAX_BULK_RECORDS):
            response = getattr(self.session, method)(
                self._bulk_records_url(table_id),
                json={"items": list(records[start:start + MAX_BULK_RECORDS])},
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list):
                raise ValueError("SmartSuite bulk response did not contain a record list.")
            created_or_updated.extend(payload)
        return created_or_updated

    def _records_url(self, table_id: str) -> str:
        self._validate_configuration()
        return f"{self.api_url}/applications/{table_id}/records/"

    def _list_records_url(self, table_id: str) -> str:
        return f"{self._records_url(table_id)}list/"

    def _bulk_records_url(self, table_id: str) -> str:
        return f"{self._records_url(table_id)}bulk/"

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
