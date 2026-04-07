"""Tests for RER_wrapper.get_organisation() - GET /Organisations/{id}"""
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
def first_org_id(wrapper):
    user = wrapper.get_user()
    return user["organisations"][0]["organisation_id"]


@pytest.fixture(scope="module")
def organisation(wrapper, first_org_id):
    return wrapper.get_organisation(first_org_id)


def test_returns_dict(organisation):
    assert isinstance(organisation, dict)


def test_organisation_id_matches_requested(organisation, first_org_id):
    assert organisation["organisation_id"] == first_org_id


def test_organisation_id_format(organisation):
    assert organisation["organisation_id"].startswith("GEN")
    assert len(organisation["organisation_id"]) == 10


def test_name_is_nonempty_string(organisation):
    assert isinstance(organisation["name"], str)
    assert len(organisation["name"]) > 0


def test_task_summary_is_list(organisation):
    assert isinstance(organisation["task_summary"], list)


def test_each_task_summary_has_required_fields(organisation):
    for task in organisation["task_summary"]:
        assert isinstance(task["task_name"], str) and len(task["task_name"]) > 0
        assert isinstance(task["task_count"], int) and task["task_count"] >= 0


def test_tabs_is_nonempty_list(organisation):
    assert isinstance(organisation["tabs"], list)
    assert len(organisation["tabs"]) > 0


def test_print_raw(organisation):
    import json
    print(json.dumps(organisation, indent=2))


def test_tabs_include_overview(organisation):
    tab_names = [t["name"] for t in organisation["tabs"]]
    assert "Overview" in tab_names
