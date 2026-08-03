from __future__ import annotations

import os
from typing import Protocol


class CookieStore(Protocol):
    def load_cookies(self) -> dict[str, str] | None:
        ...

    def save_cookies(self, cookies: dict[str, str]) -> None:
        ...


class SmartSuiteCookieStore:
    def __init__(
        self,
        api_url: str | None,
        api_token: str | None,
        app_id: str | None,
        table_id: str | None,
        record_id: str | None,
    ):
        self.api_url = api_url
        self.api_token = api_token
        self.app_id = app_id
        self.table_id = table_id
        self.record_id = record_id

    @classmethod
    def from_env(cls) -> "SmartSuiteCookieStore":
        return cls(
            api_url=os.getenv("SMARTSUITE_API_URL"),
            api_token=os.getenv("SMARTSUITE_API_TOKEN"),
            app_id=os.getenv("SMARTSUITE_APP_ID"),
            table_id=os.getenv("SMARTSUITE_TABLE_ID"),
            record_id=os.getenv("SMARTSUITE_RECORD_ID"),
        )

    def load_cookies(self) -> dict[str, str] | None:
        raise NotImplementedError(
            "Implement SmartSuite cookie retrieval in SmartSuiteCookieStore.load_cookies()."
        )

    def save_cookies(self, cookies: dict[str, str]) -> None:
        raise NotImplementedError(
            "Implement SmartSuite cookie persistence in SmartSuiteCookieStore.save_cookies()."
        )


def build_cookie_store() -> CookieStore:
    return SmartSuiteCookieStore.from_env()
