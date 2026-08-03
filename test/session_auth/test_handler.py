from __future__ import annotations

from typing import Any

from rer_session_auth.auth import RERAuthConfig
from rer_session_auth.handler import SessionAuthProxy, enrich_event_with_cookies


class StubStore:
    def __init__(self, cookies: dict[str, str] | None):
        self.cookies = cookies
        self.saved_cookies: dict[str, str] | None = None

    def load_cookies(self) -> dict[str, str] | None:
        return self.cookies

    def save_cookies(self, cookies: dict[str, str]) -> None:
        self.saved_cookies = cookies


class StubInvoker:
    def __init__(self):
        self.function_name: str | None = None
        self.payload: dict[str, Any] | None = None

    def invoke(self, function_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.function_name = function_name
        self.payload = payload
        return {"statusCode": 200, "body": '{"ok": true}'}


def make_proxy(store: StubStore, invoker: StubInvoker) -> SessionAuthProxy:
    return SessionAuthProxy(
        store=store,
        invoker=invoker,
        auth_config=RERAuthConfig(
            email="user@example.com",
            password="secret",
            gmail_token_json="{}",
            gmail_token_file=None,
        ),
        wrapper_function_name="wrapper-function",
    )


def test_proxy_uses_valid_cached_cookies(monkeypatch):
    store = StubStore({"session": "cached", "ai_session": "ignored"})
    invoker = StubInvoker()
    proxy = make_proxy(store, invoker)

    monkeypatch.setattr("rer_session_auth.handler.are_cookies_valid", lambda cookies: cookies == {"session": "cached"})

    response = proxy.handle({"path": "/user", "headers": {"X-Test": "1"}})

    assert response == {"statusCode": 200, "body": '{"ok": true}'}
    assert invoker.function_name == "wrapper-function"
    assert invoker.payload == {
        "path": "/user",
        "headers": {"X-Test": "1", "Cookie": "session=cached"},
        "auth_cookies": {"session": "cached"},
        "cookies": ["session=cached"],
    }
    assert store.saved_cookies is None


def test_proxy_refreshes_invalid_cookies(monkeypatch):
    store = StubStore({"session": "stale"})
    invoker = StubInvoker()
    proxy = make_proxy(store, invoker)

    monkeypatch.setattr("rer_session_auth.handler.are_cookies_valid", lambda cookies: False)
    monkeypatch.setattr(
        "rer_session_auth.handler.browser_authenticate_rer",
        lambda config: {"session": "fresh", "ai_debug": "drop-me"},
    )

    response = proxy.handle({"path": "/organisations/123", "headers": {}})

    assert response == {"statusCode": 200, "body": '{"ok": true}'}
    assert store.saved_cookies == {"session": "fresh"}
    assert invoker.payload == {
        "path": "/organisations/123",
        "headers": {"Cookie": "session=fresh"},
        "auth_cookies": {"session": "fresh"},
        "cookies": ["session=fresh"],
    }


def test_enrich_event_with_cookies_preserves_original_event():
    event = {"path": "/user", "headers": {"X-Test": "1"}, "cookies": ["old=1"]}

    enriched = enrich_event_with_cookies(event, {"session": "fresh"})

    assert enriched == {
        "path": "/user",
        "headers": {"X-Test": "1", "Cookie": "session=fresh"},
        "cookies": ["session=fresh"],
        "auth_cookies": {"session": "fresh"},
    }
    assert event == {"path": "/user", "headers": {"X-Test": "1"}, "cookies": ["old=1"]}
