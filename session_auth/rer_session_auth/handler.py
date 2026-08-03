from __future__ import annotations

import json
import logging
import os
from typing import Any, Protocol

from rer_session_auth.auth import (
    RERAuthConfig,
    are_cookies_valid,
    browser_authenticate_rer,
    build_cookie_header,
    sanitize_cookies,
)
from rer_session_auth.store import CookieStore, build_cookie_store


log = logging.getLogger(__name__)


class LambdaInvoker(Protocol):
    def invoke(self, function_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        ...


class Boto3LambdaInvoker:
    def __init__(self):
        import boto3  # type: ignore[import-not-found]

        self.client = boto3.client("lambda")

    def invoke(self, function_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = self.client.invoke(
            FunctionName=function_name,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload).encode("utf-8"),
        )
        response_payload = response["Payload"].read().decode("utf-8")
        if response.get("FunctionError"):
            raise RuntimeError(f"Wrapper Lambda invocation failed: {response_payload}")
        return json.loads(response_payload)


class SessionAuthProxy:
    def __init__(
        self,
        store: CookieStore,
        invoker: LambdaInvoker,
        auth_config: RERAuthConfig,
        wrapper_function_name: str,
    ):
        self.store = store
        self.invoker = invoker
        self.auth_config = auth_config
        self.wrapper_function_name = wrapper_function_name

    def handle(self, event: dict[str, Any]) -> dict[str, Any]:
        cookies = self._get_valid_cookies()
        enriched_event = enrich_event_with_cookies(event, cookies)
        return self.invoker.invoke(self.wrapper_function_name, enriched_event)

    def _get_valid_cookies(self) -> dict[str, str]:
        cached_cookies = self.store.load_cookies() or {}
        sanitized_cached_cookies = sanitize_cookies(cached_cookies)
        if sanitized_cached_cookies and are_cookies_valid(sanitized_cached_cookies):
            log.info("Using cached RER session cookies")
            return sanitized_cached_cookies

        log.info("Cached RER cookies are missing or invalid. Refreshing session.")
        refreshed_cookies = sanitize_cookies(browser_authenticate_rer(self.auth_config))
        self.store.save_cookies(refreshed_cookies)
        return refreshed_cookies


def enrich_event_with_cookies(event: dict[str, Any], cookies: dict[str, str]) -> dict[str, Any]:
    headers = dict(event.get("headers") or {})
    headers["Cookie"] = build_cookie_header(cookies)

    enriched_event = dict(event)
    enriched_event["headers"] = headers
    enriched_event["auth_cookies"] = cookies
    enriched_event["cookies"] = [f"{name}={value}" for name, value in cookies.items()]
    return enriched_event


def build_proxy() -> SessionAuthProxy:
    wrapper_function_name = os.getenv("RER_WRAPPER_FUNCTION_NAME")
    if not wrapper_function_name:
        raise RuntimeError("Set RER_WRAPPER_FUNCTION_NAME for the auth Lambda.")

    return SessionAuthProxy(
        store=build_cookie_store(),
        invoker=Boto3LambdaInvoker(),
        auth_config=RERAuthConfig.from_env(),
        wrapper_function_name=wrapper_function_name,
    )


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    del context
    return build_proxy().handle(event)
