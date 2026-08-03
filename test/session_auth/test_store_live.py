from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest
from dotenv import load_dotenv

from rer_session_auth.store import SmartSuiteCookieStore


REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_live_store() -> SmartSuiteCookieStore:
    load_dotenv(REPO_ROOT / ".env")
    store = SmartSuiteCookieStore.from_env()

    missing = [
        name
        for name, value in {
            "SMARTSUITE_API_TOKEN": store.api_token,
            "SMARTSUITE_ACCOUNT_ID": store.account_id,
            "SMARTSUITE_TABLE_ID": store.table_id,
            "SMARTSUITE_RECORD_ID": store.record_id,
            "SMARTSUITE_COOKIES_FIELD": store.cookies_field,
        }.items()
        if not value
    ]
    if missing:
        pytest.skip(f"Missing SmartSuite config for live test: {', '.join(missing)}")
    return store


def _patch_raw_fields(store: SmartSuiteCookieStore, payload: dict[str, object]) -> None:
    response = store.session.patch(store._record_url(), json=payload, timeout=store.timeout)
    response.raise_for_status()


def test_smartsuite_store_round_trip_live():
    store = _load_live_store()

    record_response = store.session.get(store._record_url(), timeout=store.timeout)
    record_response.raise_for_status()
    original_record = record_response.json()

    original_cookies_present = store.cookies_field in original_record
    original_cookies_value = original_record.get(store.cookies_field)
    original_refreshed_present = bool(store.refreshed_at_field and store.refreshed_at_field in original_record)
    original_refreshed_value = (
        original_record.get(store.refreshed_at_field)
        if store.refreshed_at_field
        else None
    )

    probe_cookies = {
        "opencode_probe": uuid.uuid4().hex,
        "opencode_probe_session": "smart-suite-round-trip",
    }

    try:
        store.save_cookies(probe_cookies)
        loaded_cookies = store.load_cookies()
        assert loaded_cookies == probe_cookies

        updated_record_response = store.session.get(store._record_url(), timeout=store.timeout)
        updated_record_response.raise_for_status()
        updated_record = updated_record_response.json()
        assert json.loads(updated_record[store.cookies_field]) == probe_cookies
    finally:
        restore_payload: dict[str, object] = {}
        if original_cookies_present:
            restore_payload[store.cookies_field] = original_cookies_value
        else:
            restore_payload[store.cookies_field] = ""

        if store.refreshed_at_field:
            if original_refreshed_present:
                restore_payload[store.refreshed_at_field] = original_refreshed_value
            else:
                restore_payload[store.refreshed_at_field] = ""

        _patch_raw_fields(store, restore_payload)
