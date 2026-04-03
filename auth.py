from playwright.sync_api import sync_playwright
import json
import os
from dotenv import load_dotenv
import logging

import requests

load_dotenv()

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def authenticate_rer(email=None, password=None, cookies_file="rer_cookies.json"):
    """Authenticate with RER portal using Azure AD B2C."""
    email = email or os.getenv("RER_EMAIL")
    password = password or os.getenv("RER_PASSWORD")

    if not email or not password:
        raise ValueError("Set RER_EMAIL and RER_PASSWORD in .env")

    log.info(f"Authenticating as {email}...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) # TODO: set true
        page = browser.new_page()

        # Navigate and wait for Azure B2C login
        log.debug("Navigating to sign-in page...")
        page.goto("https://rer.ofgem.gov.uk/Account/SignIn")
        page.wait_for_url("**/b2c_1a_rer_signin/**")

        # Fill login form
        log.debug("Filling credentials...")
        page.fill("#signInName", email)
        page.fill("#password", password)
        page.click("button:has-text('Sign in')")

        page.wait_for_load_state("networkidle")

        login_error_message = page.query_selector(selector="#localAccountForm > div.error.pageLevel > p")
        if login_error_message:
            raise ValueError(f"Authentication failed: {login_error_message.inner_text()}")

        # Manual MFA step
        log.info("\n" + "=" * 60)
        log.info("COMPLETE MFA IN THE BROWSER")
        log.info("Enter your SMS/phone code and click Continue")
        log.info("=" * 60 + "\n")

        # Wait for redirect back to RER
        log.debug("Waiting for MFA completion...")

        complete_mfa()

        page.wait_for_url("https://rer.ofgem.gov.uk/**", timeout=300000)
        log.info("Authentication successful!")

        # Save cookies
        cookies = page.context.cookies()
        with open(cookies_file, "w") as f:
            json.dump(cookies, f, indent=2)
        log.debug(f"Cookies saved to {cookies_file}")

        browser.close()
        return cookies


def complete_mfa():
    """Placeholder for MFA completion instructions."""
    log.info("\n" + "=" * 60)
    log.info("COMPLETE MFA IN THE BROWSER")
    log.info("Enter your SMS/phone code and click Continue")
    log.info("=" * 60 + "\n")


def load_cookies(cookies_file="rer_cookies.json"):
    """Load saved cookies."""
    try:
        with open(cookies_file) as f:
            return json.load(f)
    except FileNotFoundError: 
        return None


def cookies_to_dict(cookies):
    """Convert Playwright cookies to requests format."""
    return {c["name"]: c["value"] for c in cookies}


if __name__ == "__main__":
    cookies = load_cookies()

    if not cookies:
        log.info("No cookies found, authenticating...")
        cookies = authenticate_rer()
    else:
        log.info("Using saved cookies")

    cookie_dict = cookies_to_dict(cookies)
    log.info(f"\nReady: {len(cookie_dict)} cookies loaded")

    # create session
    session = requests.Session()
    session.cookies.update(cookie_dict)

    # test session
    user_details = session.get("https://rer.ofgem.gov.uk/User")  # Test authenticated request
    log.info(f"User details response: {user_details.status_code} - {user_details.text[:100]}...")
    log.info(user_details.text)

