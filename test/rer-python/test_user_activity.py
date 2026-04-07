"""Tests for RER_wrapper.get_user_activity() - GET /User/Activity"""
import sys
import os
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from dotenv import load_dotenv
from rer import RER_wrapper, UserActivity, ActivityItem

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
def activity(wrapper):
    return wrapper.get_user_activity()


def test_returns_dict(activity):
    assert isinstance(activity, dict)


def test_items_is_list(activity):
    assert isinstance(activity["items"], list)


def test_items_nonempty(activity):
    assert len(activity["items"]) > 0


def test_each_item_has_required_fields(activity):
    for item in activity["items"]:
        assert isinstance(item["title"], str) and len(item["title"]) > 0
        assert isinstance(item["by"], str)
        assert isinstance(item["datetime_iso"], str)
        assert isinstance(item["datetime_display"], str)
        assert isinstance(item["description"], str)


def test_datetime_iso_is_valid_format(activity):
    import re
    iso_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}T")
    for item in activity["items"]:
        if item["datetime_iso"]:
            assert iso_pattern.match(item["datetime_iso"]), f"Invalid ISO datetime: {item['datetime_iso']}"


def test_print_raw(activity):
    import json
    print(json.dumps(activity, indent=2))


def test_title_does_not_contain_raw_byline(activity):
    for item in activity["items"]:
        assert not item["title"].startswith("by "), f"Title starts with 'by': {item['title']}"
