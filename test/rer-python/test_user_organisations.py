"""Tests for RER_wrapper.get_user_organisations() - GET /User (all pages)"""

import json
from dataclasses import asdict
import pytest


@pytest.fixture(scope="module")
def organisations(rer):
    return rer.get_user_organisations()


def test_returns_list(organisations):
    assert isinstance(organisations, list)


def test_organisations_nonempty(organisations):
    assert len(organisations) > 0


def test_each_organisation_has_required_fields(organisations):
    for org in organisations:
        assert isinstance(org["organisation_id"], str)
        assert org["organisation_id"].startswith("GEN")
        assert isinstance(org["name"], str) and len(org["name"]) > 0
        assert isinstance(org["type"], str) and len(org["type"]) > 0
        assert isinstance(org["task_count"], int) and org["task_count"] >= 0
        assert isinstance(org["status"], str) and len(org["status"]) > 0
        assert isinstance(org["user_status"], str) and len(org["user_status"]) > 0


def test_print_raw(organisations):
    print(json.dumps(organisations, default=asdict, indent=2))
