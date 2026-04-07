"""Tests for RER_wrapper.get_user_organisations() - GET /User (all pages)"""
import sys
import os
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from dotenv import load_dotenv
from rer import RER_wrapper

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

COOKIES_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'rer_cookies.json')


@pytest.fixture(scope="module")
def wrapper():
    with open(COOKIES_FILE) as f:
        cookies = json.load(f)
    return RER_wrapper(
        cookies=cookies,
        user_email=os.getenv("RER_EMAIL"),
        user_password=os.getenv("RER_PASSWORD"),
    )


@pytest.fixture(scope="module")
def organisations(wrapper):
    return wrapper.get_user_organisations()


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
    print(json.dumps(organisations, indent=2))
