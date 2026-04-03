import base64
from time import sleep
import datetime

from playwright.sync_api import sync_playwright
import json
import os
from dotenv import load_dotenv
import logging

import requests
from gmail import get_gmail_messages
import re

load_dotenv()

logging.basicConfig(level=logging.DEBUG)
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

        # save time for retrieving MFA code 
        current_datetime = datetime.datetime.now()
        # trigger mfa code sms
        page.click('#sendCode')
        page.wait_for_load_state("networkidle")

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
            else:
                log.debug("Found error element but it's empty - assuming success")

        page.wait_for_url("https://rer.ofgem.gov.uk/**", timeout=300000)
        log.info("Authentication successful!")

        # Save cookies
        cookies = page.context.cookies()
        with open(cookies_file, "w") as f:
            json.dump(cookies, f, indent=2)
        log.debug(f"Cookies saved to {cookies_file}")

        browser.close()
        return cookies


def retrieve_mfa_code(button_clicked_after: datetime.datetime, max_retries = 3, wait_between_retries=10) -> str:
    """Extracts MFA code from email sent to energy.source.notifications@gmail.com."""
    sleep(10)  # Wait for MFA code to arrive

    for retry_number in range(max_retries):
        log.debug(f"Attempting to retrieve MFA code (try {retry_number + 1}/{max_retries})...")
        
        # Query from start of day, then filter by timestamp
        search_from = datetime.datetime.combine(button_clicked_after.date(), datetime.time.min)
        messages = get_gmail_messages(since_date=search_from, max_messages=10)

        if not messages:
            log.warning("No MFA email found yet. Retrying...")
            sleep(wait_between_retries)
            continue

        # Filter messages to only those received AFTER button was clicked
        filtered_messages = []
        for msg in messages:
            internal_date = msg.get('internalDate')
            if internal_date:
                msg_timestamp = datetime.datetime.fromtimestamp(int(internal_date) / 1000)
                log.debug(f"Message {msg['id']}: received at {msg_timestamp}, button clicked at {button_clicked_after}")
                if msg_timestamp > button_clicked_after:
                    filtered_messages.append(msg)
                else:
                    log.debug(f"  -> Skipping (too old)")
            else:
                log.warning(f"Message {msg['id']} has no internalDate, including it")
                filtered_messages.append(msg)
        
        log.debug(f"Found {len(filtered_messages)} messages received after button click")

        if not filtered_messages:
            log.warning("No new MFA emails found yet. Retrying...")
            sleep(wait_between_retries)
            continue

        # check if subject contains expected text
        for msg in filtered_messages:

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
    raise TimeoutError(f"Failed to retrieve MFA code after {max_retries} attempts.")






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

