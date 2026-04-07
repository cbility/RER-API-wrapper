"""Tests for RER_wrapper.get_user() - GET /User"""
import sys
import os
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from dotenv import load_dotenv
from rer import RER_wrapper, User, OrganisationSummary

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
def user(wrapper):
    return wrapper.get_user()


def test_returns_user_type(user):
    assert isinstance(user, dict)


def test_email_is_string_and_nonempty(user):
    assert isinstance(user["email"], str)
    assert len(user["email"]) > 0


def test_email_contains_at(user):
    assert "@" in user["email"]


def test_full_name_is_string_and_nonempty(user):
    assert isinstance(user["full_name"], str)
    assert len(user["full_name"]) > 0


def test_outstanding_tasks_is_non_negative_int(user):
    assert isinstance(user["outstanding_tasks"], int)
    assert user["outstanding_tasks"] >= 0

def test_organisations_is_list(user):
    assert isinstance(user["organisations"], list)


def test_organisations_nonempty(user):
    assert len(user["organisations"]) > 0


def test_print_raw(user):
    import json
    print(json.dumps(user, indent=2))


def test_each_organisation_has_required_fields(user):
    for org in user["organisations"]:
        assert isinstance(org["organisation_id"], str)
        assert org["organisation_id"].startswith("GEN")
        assert isinstance(org["name"], str) and len(org["name"]) > 0
        assert isinstance(org["type"], str) and len(org["type"]) > 0
        assert isinstance(org["task_count"], int) and org["task_count"] >= 0
        assert isinstance(org["status"], str) and len(org["status"]) > 0
        assert isinstance(org["user_status"], str) and len(org["user_status"]) > 0
