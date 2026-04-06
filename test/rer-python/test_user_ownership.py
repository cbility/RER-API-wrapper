"""Tests for RER_wrapper.get_user_ownership() - GET /User/Ownership"""
import sys
import os
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from dotenv import load_dotenv
from rer import RER_wrapper, UserOwnership, OwnershipSection

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
def ownership(wrapper):
    return wrapper.get_user_ownership()


def test_returns_dict(ownership):
    assert isinstance(ownership, dict)


def test_sections_is_list(ownership):
    assert isinstance(ownership["sections"], list)


def test_sections_nonempty(ownership):
    assert len(ownership["sections"]) > 0


def test_each_section_has_heading_and_content(ownership):
    for section in ownership["sections"]:
        assert isinstance(section["heading"], str) and len(section["heading"]) > 0
        assert isinstance(section["content"], str)


def test_contains_ownership_section(ownership):
    headings = [s["heading"] for s in ownership["sections"]]
    assert any("ownership" in h.lower() for h in headings)
