# region imports

from dotenv import load_dotenv # for loading environment variables from .env file
import os # for retrieving environment variables
import logging # for logging

from playwright.sync_api import sync_playwright # browser automation

import requests # lighttweight web requests

import json # for saving cookies

import base64 # for decoding email body
from time import sleep # for waiting for MFA code
import datetime # for handling timestamps
import re # for extracting MFA code from email body

from gmail import get_gmail_messages # function to retrieve Gmail messages using Gmail API

# endregion imports

# region config

# Load environment variables from .env file
load_dotenv()

# configure logging
log = logging.getLogger(__name__)

RER_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-GB,en;q=0.9",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    }

# endregion config

# region helpers

def retrieve_mfa_code(button_clicked_after: datetime.datetime, max_retries = 5, wait_between_retries=10) -> str:
    """Extracts MFA code from email sent to energy.source.notifications@gmail.com."""

    for retry_number in range(max_retries):
        log.debug(f"Attempting to retrieve MFA code (try {retry_number + 1}/{max_retries})...")
        
        # Query from start of day, then filter by timestamp
        messages_today = get_gmail_messages(since_date=button_clicked_after.date(), max_messages=10)
        messages_after_click = [
            msg for msg in messages_today
            if datetime.datetime.fromtimestamp(int(msg.get('internalDate', 0)) / 1000) > button_clicked_after
        ]

        if not messages_after_click:
            log.warning(f"No emails received after button click. Retrying in {wait_between_retries} seconds...")
            sleep(wait_between_retries)
            continue
        
        log.debug(f"Found {len(messages_after_click)} messages received after button click")

        # check if subject contains expected text
        for msg in messages_after_click:

            body = msg.get("payload", {}).get("body", {}).get("data", "")
            body_text = base64.urlsafe_b64decode(body).decode("utf-8")

            if "RER-External-prd authentication" not in body_text:
                continue # go to next message

            # assume body format: "Use verification code XXXXXX for RER-External-prd authentication."
            match = re.search(r'verification code (\d{6})', body_text)
            if match:
                mfa_code = match.group(1)
                log.info(f"Extracted MFA code: {mfa_code}")
                return mfa_code
            
        # message not found - wait before retrying
        log.debug(f"MFA email not found. Retrying in {wait_between_retries} seconds...")
        sleep(wait_between_retries)
        continue
    raise TimeoutError(f"Failed to retrieve MFA code after {max_retries} attempts.")

def save_cookies(cookies, cookies_file="../rer_cookies.json"):
    """Save cookies to a file."""
    with open(cookies_file, "w") as f:
        json.dump(cookies, f, indent=2)
    log.debug(f"Cookies saved to {cookies_file}")

def load_cookies(cookies_file="../rer_cookies.json"):
    """Load saved cookies."""
    try:
        with open(cookies_file) as f:
            return json.load(f)
    except FileNotFoundError: 
        return None


def cookies_to_dict(cookies):
    """Convert Playwright cookies to requests format."""
    return {c["name"]: c["value"] for c in cookies}

# endregion helpers

# region main

def authenticate_rer(email: str | None = None, password: str | None = None):
    """Authenticate with RER portal using Azure AD B2C."""
    email = email or os.getenv("RER_EMAIL")
    password = password or os.getenv("RER_PASSWORD")

    if not email or not password:
        raise ValueError("Set RER_EMAIL and RER_PASSWORD in .env")

    log.info(f"Authenticating with RER portal as {email}...")

    with sync_playwright() as p:
        log.debug("Launching browser...")
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

        # save time for retrieving MFA code 
        current_datetime = datetime.datetime.now()
        # trigger mfa code sms
        page.click('#sendCode')
        page.wait_for_load_state("networkidle")

        sleep(5) # initial wait for MFA code to arrive - it isn't ever quicker than this
        mfa_code = retrieve_mfa_code(button_clicked_after=current_datetime)

        page.fill("#verificationCode", mfa_code)
        page.click('#verifyCode')
        page.wait_for_load_state("networkidle")
        
        error_message = page.query_selector('div.error:nth-child(2)')
        if error_message:
            error_text = error_message.inner_text()
            if error_text.strip():  # Only raise if there's actual error text
                log.error(f"MFA verification error element: {error_text}")
                raise ValueError(f"MFA verification failed: {error_text}")

        page.wait_for_url("https://rer.ofgem.gov.uk/**", timeout=300000)
        log.info("Authentication successful!")

        # Save cookies
        cookies = page.context.cookies()

        browser.close()
        return cookies

# endregion main

# region testing

if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG) # debug logging for testing

    headers = RER_HEADERS
    cookies = load_cookies()

    if not cookies:
        log.info("No cookies found, authenticating...")
        cookies = authenticate_rer()
        save_cookies(cookies)

    cookie_dict = cookies_to_dict(cookies)
    log.debug(f"\nReady: {len(cookie_dict)} cookies loaded")

    # create session
    session = requests.Session()
    session.cookies.update(cookie_dict)
    session.headers.update(headers)

    # test session
    user_details = session.get("https://rer.ofgem.gov.uk/User")  # Test authenticated request
    log.info(f"User details response: {user_details.status_code} (final URL: {user_details.url})")
    log.debug(user_details.text[:5000])


# endregion testing

