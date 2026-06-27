"""Tests for RER_wrapper.get_organisation_station_declarations() - GET /Organisations/{id}/Tasks/StationDeclarations"""
import os
import json
import pytest
import re

from rer_api_wrapper import RER_wrapper
from rer_api_wrapper.models import StationDeclarationTaskList, to_dict


COOKIES_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'rer_cookies.json')

YEAR_RE = re.compile(r'^\d{4}/\d{4}$')


@pytest.fixture(scope="module")
def wrapper():
    with open(COOKIES_FILE) as f:
        cookies = json.load(f)
    return RER_wrapper(auth_cookies=cookies)


@pytest.fixture(scope="module")
def first_org_id(wrapper):
    return wrapper.get_user_organisations()[0].organisation_id


@pytest.fixture(scope="module")
def declarations(wrapper, first_org_id):
    return wrapper.get_organisation_station_declarations(first_org_id)


def test_returns_dict(declarations):
    assert isinstance(declarations, StationDeclarationTaskList)


def test_organisation_id_is_correct(declarations, first_org_id):
    assert declarations["organisation_id"] == first_org_id


def test_tasks_is_list(declarations):
    assert isinstance(declarations["tasks"], list)


def test_each_task_has_required_fields(declarations):
    for task in declarations["tasks"]:
        assert isinstance(task["declaration_type"], str) and len(task["declaration_type"]) > 0
        assert isinstance(task["year"], str)
        assert isinstance(task["url"], str)


def test_print_raw(declarations):
    print(json.dumps(to_dict(declarations), indent=2))


def test_year_format(declarations):
    for task in declarations["tasks"]:
        if task["year"]:
            assert YEAR_RE.match(task["year"]), f"Unexpected year format: {task['year']}"
