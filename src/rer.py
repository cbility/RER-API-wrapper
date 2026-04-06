# region imports

from dotenv import load_dotenv # for loading environment variables from .env file
import os # for retrieving environment variables
import logging # for logging

import requests # lighttweight web requests

from bs4 import BeautifulSoup # for parsing HTML

import json # for saving cookies

import base64 # for decoding email body
from time import sleep # for waiting for MFA code
import datetime # for handling timestamps
import re # for extracting MFA code from email body

from gmail import get_gmail_messages # function to retrieve Gmail messages using Gmail API

# endregion imports

# region config

# configure logging
log = logging.getLogger(__name__)

RER_DEFAULT_HEADERS = {
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

def _browser_authenticate_rer(email: str, password: str) -> dict:
    """Authenticate with RER portal using Azure AD B2C."""
    from playwright.sync_api import sync_playwright # browser automation

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
        log.debug("Triggering MFA code...")
        page.click('#sendCode')
        page.wait_for_load_state("networkidle")

        sleep(5) # initial wait for MFA code to arrive - it isn't ever quicker than this
        mfa_code = _retrieve_mfa_code(button_clicked_after=current_datetime)

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
        cookies_dict = {c["name"]: c["value"] for c in cookies}

        browser.close()
        return cookies_dict

def _retrieve_mfa_code(button_clicked_after: datetime.datetime, max_retries = 5, wait_between_retries=10) -> str:
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
            log.warning(f"No emails received after button click ({button_clicked_after}). Retrying in {wait_between_retries} seconds...")
            sleep(wait_between_retries)
            continue
        
        log.debug(f"Found {len(messages_after_click)} messages received after button click ({button_clicked_after})")

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


# endregion helpers

# region class

class RER_wrapper:
    """Wrapper for authenticating with RER portal and making authenticated requests.
    
    Params:
        cookies: Optional dict of cookies to use for authentication. If not provided, will authenticate via browser automation.
        headers: Optional dict of headers to use for requests. Defaults to RER_DEFAULT_HEADERS.
    """
    session: requests.Session
    base_url="https://rer.ofgem.gov.uk/"
    __user_email: str | None = None
    __user_password: str | None = None

    def __init__(self, cookies: dict | None = None, user_email: str | None = None, user_password: str | None = None, headers: dict = RER_DEFAULT_HEADERS):
        self.__user_email = user_email
        self.__user_password = user_password
        self.cookies = cookies
        self.headers = headers

        self.authenticate(cookies, headers)
    
    def get_cookies(self) -> dict:
        """Get current session cookies."""
        return self.session.cookies.get_dict()
   
    def authenticate(
            self,   
            cookies: dict | None,
            headers: dict = RER_DEFAULT_HEADERS) -> None:
        """Authenticate with RER portal and set session.

        If cookies are provided, creates a session with the provided cookies. 
        If cookies are not provided, or the created session is invalid, creates 
        a new session by automating a browser and logging into the portal.
        """

        session = requests.Session()
        session.headers.update(headers)

        if cookies:
            session.cookies.update(cookies)
            self.session = session
            try:
                # test session
                self.__user_email = self.get_user_email()
                log.info(f"Authenticated as {self.__user_email} using stored cookies.")
                return
            except Exception as e:
                log.warning(f"Stored cookies are invalid: {e}. Re-authenticating...")
        else:
            log.debug("No stored cookies, authenticating...")

        # no cookies provided or session invalid - authenticate via browser automation
        
        cookies = _browser_authenticate_rer(email=self.__user_email, password=self.__user_password)
        session.cookies.update(cookies)
        self.session = session

        self.__user_email = self.get_user_email()
        log.info(f"Authenticated as {self.__user_email} using new session.")
        return

    def get_user_email(self) -> str:
        """Get the email address of the authenticated user."""
        response = self.session.get(self.base_url + "User")
        response.raise_for_status()
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            h1 = soup.find("h1", class_="govuk-heading-xl")
            email = h1.find("span", class_="govuk-caption-l").get_text(strip=True).split(",")[-1].strip()
            return email
        elif response.status_code == 403:
            raise Exception(f"Could not retrieve user email: Invalid session: {response.status_code}")
        else:
            log.error(f"Unexpected response when retrieving user email: {response.status_code} - {response.text}")
            raise Exception(f"Could not retrieve user email: {response.status_code}")
# endregion class


# region helpers


# endregion helpers


# region testing

if __name__ == "__main__":

    def _save_cookies(cookies, cookies_file="../rer_cookies.json"):
        """Save cookies to a file."""
        with open(cookies_file, "w") as f:
            json.dump(cookies, f, indent=2)
        log.debug(f"Cookies saved to {cookies_file}")

    def _load_cookies(cookies_file="../rer_cookies.json"):
        """Load saved cookies."""
        try:
            with open(cookies_file) as f:
                return json.load(f)
        except FileNotFoundError: 
            return None

    def _cookies_to_dict(cookies):
        """Convert Playwright cookies to requests format."""
        return {c["name"]: c["value"] for c in cookies}

    # Load environment variables from .env file
    load_dotenv()

    if not os.getenv("RER_EMAIL") or not os.getenv("RER_PASSWORD"):
        raise ValueError("Please set RER_EMAIL and RER_PASSWORD environment variables in .env file")

    logging.basicConfig(level=logging.DEBUG) # debug logging for testing

    cookies = _load_cookies()
    cookies = None
    if cookies:
        log.debug("Loaded cookies from file")
        cookies = _cookies_to_dict(cookies)
    else:
        log.debug("No cookies found in file, will authenticate via browser")

    rer = RER_wrapper(cookies=cookies, user_email=os.getenv("RER_EMAIL"), user_password=os.getenv("RER_PASSWORD"))

    # Save cookies for future use
    _save_cookies(rer.get_cookies())

# endregion testing

