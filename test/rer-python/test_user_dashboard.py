"""Tests for RER_wrapper.get_user_dashboard() - GET /User"""
import sys
import os
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from dotenv import load_dotenv
from rer import RER_wrapper, UserDashboard, OrganisationSummary

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
def dashboard(wrapper):
    return wrapper.get_user_dashboard()


def test_returns_user_dashboard_type(dashboard):
    assert isinstance(dashboard, dict)


def test_email_is_string_and_nonempty(dashboard):
    assert isinstance(dashboard["email"], str)
    assert len(dashboard["email"]) > 0


def test_email_contains_at(dashboard):
    assert "@" in dashboard["email"]


def test_full_name_is_string_and_nonempty(dashboard):
    assert isinstance(dashboard["full_name"], str)
    assert len(dashboard["full_name"]) > 0


def test_outstanding_tasks_is_non_negative_int(dashboard):
    assert isinstance(dashboard["outstanding_tasks"], int)
    assert dashboard["outstanding_tasks"] >= 0


def test_active_organisations_is_positive_int(dashboard):
    assert isinstance(dashboard["active_organisations"], int)
    assert dashboard["active_organisations"] > 0


def test_organisations_is_list(dashboard):
    assert isinstance(dashboard["organisations"], list)


def test_organisations_nonempty(dashboard):
    assert len(dashboard["organisations"]) > 0


def test_each_organisation_has_required_fields(dashboard):
    for org in dashboard["organisations"]:
        assert isinstance(org["organisation_id"], str)
        assert org["organisation_id"].startswith("GEN")
        assert isinstance(org["name"], str) and len(org["name"]) > 0
        assert isinstance(org["type"], str) and len(org["type"]) > 0
        assert isinstance(org["task_count"], int) and org["task_count"] >= 0
        assert isinstance(org["status"], str) and len(org["status"]) > 0
        assert isinstance(org["user_status"], str) and len(org["user_status"]) > 0
