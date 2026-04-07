"""Tests for RER_wrapper.get_organisation_output_data() - GET /Organisations/{id}/Tasks/OutputData"""
import sys
import os
import json
import pytest
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from dotenv import load_dotenv
from rer import RER_wrapper

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

COOKIES_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'rer_cookies.json')

UUID_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)


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
    return wrapper.get_user_organisations()[0]["organisation_id"]


@pytest.fixture(scope="module")
def output_data(wrapper, first_org_id):
    return wrapper.get_organisation_output_data(first_org_id)


def test_returns_dict(output_data):
    assert isinstance(output_data, dict)


def test_organisation_id_is_correct(output_data, first_org_id):
    assert output_data["organisation_id"] == first_org_id


def test_tasks_is_list(output_data):
    assert isinstance(output_data["tasks"], list)


def test_tasks_nonempty(output_data):
    assert len(output_data["tasks"]) > 0


def test_each_task_has_required_fields(output_data):
    for task in output_data["tasks"]:
        assert isinstance(task["task_id"], str) and len(task["task_id"]) > 0
        assert isinstance(task["period"], str) and len(task["period"]) > 0
        assert isinstance(task["station_name"], str) and len(task["station_name"]) > 0
        assert isinstance(task["status"], str) and len(task["status"]) > 0
        assert isinstance(task["url"], str) and len(task["url"]) > 0


def test_print_raw(output_data):
    import json
    print(json.dumps(output_data, indent=2))


def test_task_ids_are_uuids(output_data):
    for task in output_data["tasks"]:
        assert UUID_RE.match(task["task_id"]), f"Not a UUID: {task['task_id']}"
