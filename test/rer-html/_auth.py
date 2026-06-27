"""Shared cookie authentication helper for HTML-fetching scripts."""
import sys
import os
import json
import logging

# Add src/ to path so rer.py can be imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from rer import RER_wrapper

logging.basicConfig(level=logging.INFO)

COOKIES_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'rer_cookies.json')


def load_cookies(cookies_file: str = COOKIES_FILE) -> dict:
    try:
        with open(cookies_file) as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Cookies file not found at {cookies_file}. Provide authenticated RER cookies before fetching HTML."
        )


def save_cookies(cookies: dict, cookies_file: str = COOKIES_FILE) -> None:
    with open(cookies_file, 'w') as f:
        json.dump(cookies, f, indent=2)


def get_wrapper() -> RER_wrapper:
    cookies = load_cookies()
    wrapper = RER_wrapper(auth_cookies=cookies)
    save_cookies(wrapper.get_cookies())
    return wrapper
