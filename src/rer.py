# region imports

from dotenv import load_dotenv # for loading environment variables from .env file
import os # for retrieving environment variables
import logging # for logging
import datetime # for handling timestamps

import requests # lighttweight web requests

from selectolax.parser import HTMLParser # for parsing HTML

import json # for saving cookies

from typing import TypedDict, Optional

# endregion imports

# region types

class OrganisationSummary(TypedDict):
    organisation_id: str
    name: str
    type: str
    task_count: int
    status: str
    user_status: str

class User(TypedDict):
    email: str
    full_name: str
    outstanding_tasks: int
    active_organisations: int
    organisations: list[OrganisationSummary]

class ActivityItem(TypedDict):
    title: str
    by: str
    datetime_iso: str
    datetime_display: str
    description: str

class UserActivity(TypedDict):
    items: list[ActivityItem]

class OwnershipSection(TypedDict):
    heading: str
    content: str

class UserOwnership(TypedDict):
    sections: list[OwnershipSection]

class NotificationCategory(TypedDict):
    category: str
    manage_url: str

class UserNotifications(TypedDict):
    categories: list[NotificationCategory]

class OrganisationTaskSummary(TypedDict):
    task_name: str
    task_count: int

class OrganisationTab(TypedDict):
    name: str
    url: str

class OrganisationDetail(TypedDict):
    organisation_id: str
    name: str
    task_summary: list[OrganisationTaskSummary]
    tabs: list[OrganisationTab]

class OutputDataTask(TypedDict):
    task_id: str
    period: str
    station_name: str
    status: str
    url: str

class OutputDataTaskList(TypedDict):
    organisation_id: str
    tasks: list[OutputDataTask]

class StationDeclarationTask(TypedDict):
    declaration_type: str
    year: str
    url: str

class StationDeclarationTaskList(TypedDict):
    organisation_id: str
    tasks: list[StationDeclarationTask]

# endregion types

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
    from time import sleep # for waiting for MFA code

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

    import base64 # for decoding email body
    from time import sleep # for waiting for MFA code
    
    import re # for extracting MFA code from email body
    from gmail import get_gmail_messages

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

# region parsers

def _parse_user(html: str) -> User:
    tree = HTMLParser(html)

    h1 = tree.css_first("h1.govuk-heading-xl")
    caption = h1.css_first("span.govuk-caption-l")
    email = caption.text(strip=True).split(",")[-1].strip()

    # Remove caption, links, and spans to isolate the full name
    caption.decompose()
    for node in h1.css("a"):
        node.decompose()
    for node in h1.css("span"):
        node.decompose()
    full_name = h1.text(strip=True)

    # Stats
    outstanding_tasks = 0
    active_organisations = 0
    for item in tree.css(".ofgem-rer-stat__item"):
        parts = item.text(separator="|", strip=True).split("|")
        if len(parts) == 2:
            count_str, label = parts[0], parts[1].lower()
            try:
                count = int(count_str.replace(",", ""))
            except ValueError:
                count = 0
            if "task" in label:
                outstanding_tasks = count
            elif "organisation" in label:
                active_organisations = count

    # Organisations table
    organisations: list[OrganisationSummary] = []
    for row in tree.css("table tr")[1:]:
        cells = row.css("td")
        if not cells:
            continue
        org_link = cells[0].css_first("a")
        org_id = ""
        if org_link:
            href = org_link.attrs.get("href", "")
            org_id = href.split("/Organisations/")[-1].split("/")[0]
        organisations.append(OrganisationSummary(
            organisation_id=org_id,
            name=cells[0].text(strip=True),
            type=cells[1].text(strip=True),
            task_count=int(cells[2].text(strip=True) or 0),
            status=cells[3].text(strip=True),
            user_status=cells[4].text(strip=True),
        ))

    return User(
        email=email,
        full_name=full_name,
        outstanding_tasks=outstanding_tasks,
        active_organisations=active_organisations,
        organisations=organisations,
    )

def _parse_organisation(html: str) -> OrganisationDetail:
    tree = HTMLParser(html)

    h1 = tree.css_first("h1.govuk-heading-xl")
    caption = h1.css_first("span.govuk-caption-l") if h1 else None
    org_id = ""
    if caption:
        org_id = caption.text(strip=True).split(",")[-1].strip()
        caption.decompose()
    name = h1.text(strip=True) if h1 else ""

    # Task summary table
    task_summary: list[OrganisationTaskSummary] = []
    for row in tree.css("table tr")[1:]:
        cells = row.css("td")
        if len(cells) >= 2:
            task_name = cells[0].text(strip=True)
            try:
                task_count = int(cells[1].text(strip=True))
            except ValueError:
                task_count = 0
            task_summary.append(OrganisationTaskSummary(task_name=task_name, task_count=task_count))

    # Tab navigation
    tabs: list[OrganisationTab] = [
        OrganisationTab(name=a.text(strip=True), url=a.attrs.get("href", ""))
        for a in tree.css(".moj-sub-navigation a")
    ]

    return OrganisationDetail(organisation_id=org_id, name=name, task_summary=task_summary, tabs=tabs)


def _parse_output_data_tasks(html: str, organisation_id: str) -> OutputDataTaskList:
    tree = HTMLParser(html)
    tasks: list[OutputDataTask] = []

    for row in tree.css("table tr")[1:]:
        cells = row.css("td")
        if len(cells) < 4:
            continue
        link = cells[0].css_first("a")
        url = link.attrs.get("href", "") if link else ""
        # Extract task ID from /Output/{uuid}/...
        task_id = ""
        url_parts = url.split("/")
        output_idx = next((i for i, p in enumerate(url_parts) if p == "Output"), None)
        if output_idx is not None and output_idx + 1 < len(url_parts):
            task_id = url_parts[output_idx + 1].split("?")[0]

        tasks.append(OutputDataTask(
            task_id=task_id,
            period=cells[0].text(strip=True),
            station_name=cells[1].text(strip=True),
            status=cells[3].text(strip=True),
            url=url,
        ))

    return OutputDataTaskList(organisation_id=organisation_id, tasks=tasks)


def _parse_station_declaration_tasks(html: str, organisation_id: str) -> StationDeclarationTaskList:
    tree = HTMLParser(html)
    tasks: list[StationDeclarationTask] = []

    for row in tree.css("table tr")[1:]:
        cells = row.css("td")
        if len(cells) < 2:
            continue
        link = cells[0].css_first("a")
        url = link.attrs.get("href", "") if link else ""
        tasks.append(StationDeclarationTask(
            declaration_type=cells[0].text(strip=True),
            year=cells[1].text(strip=True),
            url=url,
        ))

    return StationDeclarationTaskList(organisation_id=organisation_id, tasks=tasks)

# endregion parsers

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
    has_fresh_cookies: bool = False

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
        self.has_fresh_cookies = True
        return
    
    def _request(self, endpoint: str, method: str = "GET", **kwargs) -> requests.Response:
        """Make an authenticated request to the RER portal."""
        url = self.base_url + endpoint.lstrip("/")
        response = self.session.request(method, url, **kwargs)
        if response.status_code == 200:
            return response
        elif response.status_code == 403:
            raise Exception(f"Authentication failed: {response.status_code}")
        else:
            log.error(f"Unexpected response when making request to {endpoint}: {response.status_code} - {response.text}")
            response.raise_for_status()
        return response

    def get_user_email(self) -> str:
        """Get the email address of the authenticated user."""
        response = self.session.get(self.base_url + "User")
        response.raise_for_status()
        if response.status_code == 200:
            tree = HTMLParser(response.text)
            caption = tree.css_first("h1.govuk-heading-xl span.govuk-caption-l")
            email = caption.text(strip=True).split(",")[-1].strip()
            return email
        elif response.status_code == 403:
            raise Exception(f"Could not retrieve user email: Invalid session: {response.status_code}")
        else:
            log.error(f"Unexpected response when retrieving user email: {response.status_code} - {response.text}")
            raise Exception(f"Could not retrieve user email: {response.status_code}")

    def get_user(self, sort_field: str | None = None, sort_direction: str | None = None, page_number: int = 1) -> User:
        """GET /User - Returns user dashboard with stats and organisation list."""
        params: dict = {"pageNumber": page_number}
        if sort_field:
            params["sortField"] = sort_field
        if sort_direction:
            params["sortDirection"] = sort_direction

        response = self._request("User", params=params)
        return _parse_user(response.text)

    def get_organisation(self, organisation_id: str) -> OrganisationDetail:
        """GET /Organisations/{organisationId} - Returns organisation overview."""
        response = self._request(f"Organisations/{organisation_id}")
        return _parse_organisation(response.text)

    def get_organisation_output_data(
        self,
        organisation_id: str,
        statuses: list[str] | None = None,
        sort_field: str | None = None,
        sort_direction: str | None = None,
        page_number: int = 1,
    ) -> OutputDataTaskList:
        """GET /Organisations/{organisationId}/Tasks/OutputData - Returns output data tasks."""
        params: dict = {"pageNumber": page_number}
        if statuses:
            params["Statuses"] = statuses
        if sort_field:
            params["sortField"] = sort_field
        if sort_direction:
            params["sortDirection"] = sort_direction
        response = self._request(f"Organisations/{organisation_id}/Tasks/OutputData", params=params)
        return _parse_output_data_tasks(response.text, organisation_id)

    def get_organisation_station_declarations(
        self,
        organisation_id: str,
        sort_field: str | None = None,
        sort_direction: str | None = None,
        page_number: int = 1,
    ) -> StationDeclarationTaskList:
        """GET /Organisations/{organisationId}/Tasks/StationDeclarations - Returns station declaration tasks."""
        params: dict = {"pageNumber": page_number}
        if sort_field:
            params["sortField"] = sort_field
        if sort_direction:
            params["sortDirection"] = sort_direction
        response = self.session.get(
            self.base_url + f"Organisations/{organisation_id}/Tasks/StationDeclarations",
            params=params,
        )
        response.raise_for_status()
        return _parse_station_declaration_tasks(response.text, organisation_id)

# endregion class

# region testing

if __name__ == "__main__":

    def _save_cookies(cookies, cookies_file="../rer_cookies.json"):
        """Save cookies to a file."""
        # remove analytics/tracking cookies
        persistent_cookies = {key: value for key, value in cookies.items() if not key.startswith("ai_")}
        with open(cookies_file, "w") as f:
            json.dump(persistent_cookies, f, indent=2)
        log.debug(f"Cookies saved to {cookies_file}")

    def _load_cookies(cookies_file="../rer_cookies.json") -> dict:
        """Load saved cookies."""
        try:
            with open(cookies_file) as f:
                return json.load(f)
        except FileNotFoundError: 
            return None

    # Load environment variables from .env file
    load_dotenv()

    if not os.getenv("RER_EMAIL") or not os.getenv("RER_PASSWORD"):
        raise ValueError("Please set RER_EMAIL and RER_PASSWORD environment variables in .env file")

    logging.basicConfig(level=logging.DEBUG) # debug logging for testing

    cookies = _load_cookies()
    if cookies:
        log.debug("Loaded cookies from file")
    else:
        log.debug("No cookies found in file, will authenticate via browser")

    rer = RER_wrapper(cookies=cookies, user_email=os.getenv("RER_EMAIL"), user_password=os.getenv("RER_PASSWORD"))

    # Save cookies for future use
    if rer.has_fresh_cookies:
        _save_cookies(rer.get_cookies())

# endregion testing

