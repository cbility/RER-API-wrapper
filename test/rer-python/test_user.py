"""Tests for RER_wrapper.get_user() - GET /User"""
import os
import json
import pytest

from rer_api_wrapper import RER_wrapper
from rer_api_wrapper.models import User, to_dict


COOKIES_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'rer_cookies.json')


@pytest.fixture(scope="module")
def wrapper():
    with open(COOKIES_FILE) as f:
        cookies = json.load(f)
    return RER_wrapper(auth_cookies=cookies)


@pytest.fixture(scope="module")
def user(wrapper):
    return wrapper.get_user()


def test_returns_user_type(user):
    assert isinstance(user, User)


def test_email_is_string_and_nonempty(user):
    assert isinstance(user.email, str)
    assert len(user.email) > 0


def test_email_contains_at(user):
    assert "@" in user.email


def test_full_name_is_string_and_nonempty(user):
    assert isinstance(user.full_name, str)
    assert len(user.full_name) > 0


def test_outstanding_tasks_is_non_negative_int(user):
    assert isinstance(user.outstanding_tasks, int)
    assert user.outstanding_tasks >= 0

def test_print_raw(user):
    print(json.dumps(to_dict(user), indent=2))
