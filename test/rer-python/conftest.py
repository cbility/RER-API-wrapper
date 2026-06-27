"""Shared setup for live RER integration tests."""
import json
import os
import sys

import pytest
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from rer import RER_wrapper


COOKIES_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "rer_cookies.json")


@pytest.fixture(scope="session", autouse=True)
def require_valid_rer_cookies():
    try:
        with open(COOKIES_FILE) as f:
            cookies = json.load(f)
        RER_wrapper(auth_cookies=cookies)
    except FileNotFoundError:
        pytest.skip(f"RER cookie file not found: {COOKIES_FILE}", allow_module_level=True)
    except (ValueError, requests.exceptions.RequestException) as exc:
        pytest.skip(f"RER cookies are unavailable or invalid: {exc}", allow_module_level=True)
