"""Tests for RER_wrapper.get_user_notifications() - GET /User/Notifications"""
import sys
import os
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from dotenv import load_dotenv
from rer import RER_wrapper, UserNotifications, NotificationCategory

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
def notifications(wrapper):
    return wrapper.get_user_notifications()


def test_returns_dict(notifications):
    assert isinstance(notifications, dict)


def test_categories_is_list(notifications):
    assert isinstance(notifications["categories"], list)


def test_categories_nonempty(notifications):
    assert len(notifications["categories"]) > 0


def test_each_category_has_required_fields(notifications):
    for cat in notifications["categories"]:
        assert isinstance(cat["category"], str) and len(cat["category"]) > 0
        assert isinstance(cat["manage_url"], str) and len(cat["manage_url"]) > 0


def test_manage_urls_contain_notifications_path(notifications):
    for cat in notifications["categories"]:
        assert "/Notifications/" in cat["manage_url"], f"Unexpected URL: {cat['manage_url']}"
