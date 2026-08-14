from __future__ import annotations

import pytest

from rer_scraper.smartsuite import (
    SmartSuiteClient,
    SmartSuiteFilter,
    SmartSuiteFilterGroup,
    SmartSuiteSort,
)


class StubResponse:
    def __init__(self, payload: object):
        self.payload = payload

    def json(self) -> object:
        return self.payload

    def raise_for_status(self) -> None:
        pass


class StubSession:
    def __init__(self):
        self.headers: dict[str, str] = {}
        self.get_calls: list[tuple[str, int]] = []
        self.post_calls: list[tuple[str, dict[str, object], int]] = []
        self.patch_calls: list[tuple[str, dict[str, object], int]] = []
        self.list_responses: list[object] = []

    def post(self, url: str, json: dict[str, object], timeout: int, params=None) -> StubResponse:
        self.post_calls.append((url, json, timeout))
        if url.endswith("/list/"):
            if self.list_responses:
                return StubResponse(self.list_responses.pop(0))
            return StubResponse({"items": [{"id": "record-1"}]})
        if url.endswith("/bulk/"):
            return StubResponse(json["items"])
        return StubResponse({"id": "record-2", **json})

    def get(self, url: str, timeout: int) -> StubResponse:
        self.get_calls.append((url, timeout))
        return StubResponse({"id": "record-1"})

    def patch(self, url: str, json: dict[str, object], timeout: int) -> StubResponse:
        self.patch_calls.append((url, json, timeout))
        if url.endswith("/bulk/"):
            return StubResponse(json["items"])
        return StubResponse({"id": "record-1", **json})


def make_client() -> SmartSuiteClient:
    client = SmartSuiteClient(
        api_url="https://app.smartsuite.com/api/v1",
        api_token="token",
        account_id="account",
        timeout=12,
    )
    client.session = StubSession()  # type: ignore[assignment]
    return client


def test_get_record_uses_record_endpoint():
    client = make_client()

    record = client._get_record("table-1", "record-1")

    assert record == {"id": "record-1"}
    assert client.session.get_calls == [  # type: ignore[attr-defined]
        ("https://app.smartsuite.com/api/v1/applications/table-1/records/record-1/", 12)
    ]


def test_create_record_posts_fields_to_table_endpoint():
    client = make_client()

    record = client._create_record("table-1", {"field": "value"})

    assert record == {"id": "record-2", "field": "value"}
    assert client.session.post_calls == [  # type: ignore[attr-defined]
        ("https://app.smartsuite.com/api/v1/applications/table-1/records/", {"field": "value"}, 12)
    ]


def test_update_record_patches_fields_to_record_endpoint():
    client = make_client()

    record = client._update_record("table-1", "record-1", {"field": "value"})

    assert record == {"id": "record-1", "field": "value"}
    assert client.session.patch_calls == [  # type: ignore[attr-defined]
        ("https://app.smartsuite.com/api/v1/applications/table-1/records/record-1/", {"field": "value"}, 12)
    ]


def test_list_records_posts_typed_filter_and_sort():
    client = make_client()
    records = client._list_records(
        "table-1",
        filter_group=SmartSuiteFilterGroup(
            operator="and",
            fields=[SmartSuiteFilter(field="status", comparison="is_not", value="Complete")],
        ),
        sorts=[SmartSuiteSort(field="title", direction="desc")],
        hydrated=True,
    )

    assert records == [{"id": "record-1"}]
    assert client.session.post_calls == [  # type: ignore[attr-defined]
        (
            "https://app.smartsuite.com/api/v1/applications/table-1/records/list/",
            {
                "filter": {
                    "operator": "and",
                    "fields": [{"field": "status", "comparison": "is_not", "value": "Complete"}],
                },
                "sort": [{"field": "title", "direction": "desc"}],
                "hydrated": True,
            },
            12,
        )
    ]


def test_list_records_follows_offset_pagination():
    client = make_client()
    client.session.list_responses = [  # type: ignore[attr-defined]
        {"total": 3, "items": [{"id": "record-1"}, {"id": "record-2"}]},
        {"total": 3, "items": [{"id": "record-3"}]},
    ]

    records = client._list_records("table-1", page_size=2)

    assert records == [{"id": "record-1"}, {"id": "record-2"}, {"id": "record-3"}]
    assert len(client.session.post_calls) == 2  # type: ignore[attr-defined]


def test_bulk_add_splits_records_into_batches_of_25():
    client = make_client()
    records = [{"title": f"record-{number}"} for number in range(26)]

    created = client._bulk_add_records("table-1", records)

    assert created == records
    assert [len(call[1]["items"]) for call in client.session.post_calls] == [25, 1]  # type: ignore[attr-defined]
    assert all(call[0].endswith("/records/bulk/") for call in client.session.post_calls)  # type: ignore[attr-defined]


def test_bulk_update_splits_records_into_batches_of_25():
    client = make_client()
    records = [{"id": f"record-{number}", "title": f"record-{number}"} for number in range(26)]

    updated = client._bulk_update_records("table-1", records)

    assert updated == records
    assert [len(call[1]["items"]) for call in client.session.patch_calls] == [25, 1]  # type: ignore[attr-defined]
    assert all(call[0].endswith("/records/bulk/") for call in client.session.patch_calls)  # type: ignore[attr-defined]


def test_bulk_update_requires_record_ids():
    client = make_client()

    with pytest.raises(ValueError, match="include an id"):
        client._bulk_update_records("table-1", [{"title": "missing id"}])