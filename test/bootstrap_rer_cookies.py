"""Manually regenerate RER cookies using browser/MFA flow.

Run from the repository root:
    uv run python test/bootstrap_rer_cookies.py
"""
import argparse
import base64
import datetime
import json
import logging
import os
import re
from pathlib import Path
from time import sleep
from typing import NotRequired, TypedDict

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build # type: ignore
from playwright.sync_api import sync_playwright


log = logging.getLogger(__name__)
REPO_ROOT = Path(__file__).resolve().parents[1]
GMAIL_SCOPES = ["https://mail.google.com/"]


class GmailMessageBody(TypedDict):
    data: str
    size: int
    attachmentId: NotRequired[str]


class GmailMessagePart(TypedDict, total=False):
    partId: str
    mimeType: str
    filename: str
    body: GmailMessageBody
    parts: list["GmailMessagePart"]


class GmailMessagePayload(TypedDict, total=False):
    partId: str
    mimeType: str
    filename: str
    body: GmailMessageBody
    parts: list[GmailMessagePart]


class GmailMessage(TypedDict):
    id: str
    threadId: str
    payload: NotRequired[GmailMessagePayload]
    internalDate: NotRequired[str]


def get_no_token_error_message(token_file_path: Path) -> str:
    return f"""
{'=' * 80}
ERROR: {token_file_path} not found
{'=' * 80}
Gmail API requires OAuth2 authentication. Follow these steps:
1. Create OAuth2 desktop app credentials in Google Cloud Console.
2. Enable the Gmail API.
3. Add your Gmail address as a test user if the OAuth app is in testing.
4. Run an OAuth flow that writes {token_file_path}.

Example:
    from google_auth_oauthlib.flow import InstalledAppFlow
    flow = InstalledAppFlow.from_client_secrets_file(
        "gmail_credentials.json",
        ["https://mail.google.com/"],
    )
    creds = flow.run_local_server(port=0)
    with open(r"{token_file_path}", "w") as f:
        f.write(creds.to_json())
{'=' * 80}
"""


def get_gmail_messages(
    since_date: datetime.date,
    max_messages: int,
    token_file: Path,
) -> list[GmailMessage]:
    if not token_file.exists():
        raise FileNotFoundError(get_no_token_error_message(token_file))

    creds = Credentials.from_authorized_user_file(token_file, GMAIL_SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_file.write_text(creds.to_json(), encoding="utf-8")

    service = build("gmail", "v1", credentials=creds)
    query = f'after:{since_date.strftime("%Y/%m/%d")}'
    results = service.users().messages().list(userId="me", q=query, maxResults=max_messages).execute()
    message_refs = results.get("messages", [])

    messages: list[GmailMessage] = []
    for msg_ref in message_refs:
        msg = service.users().messages().get(userId="me", id=msg_ref["id"], format="full").execute()
        messages.append(msg)
    return messages


def decode_message_body(payload: GmailMessagePayload | GmailMessagePart | None) -> str:
    if not payload:
        return ""

    body = payload.get("body", {})
    data = body.get("data")
    if data:
        return base64.urlsafe_b64decode(data).decode("utf-8")

    return "\n".join(decode_message_body(part) for part in payload.get("parts", []))


def retrieve_mfa_code(
    button_clicked_after: datetime.datetime,
    token_file: Path,
    max_retries: int,
    wait_between_retries: int,
) -> str:
    for retry_number in range(max_retries):
        log.info("Attempting to retrieve MFA code (%s/%s)", retry_number + 1, max_retries)
        messages_today = get_gmail_messages(
            since_date=button_clicked_after.date(),
            max_messages=10,
            token_file=token_file,
        )
        messages_after_click = [
            msg
            for msg in messages_today
            if datetime.datetime.fromtimestamp(int(msg.get("internalDate", 0)) / 1000) > button_clicked_after
        ]

        for msg in messages_after_click:
            body_text = decode_message_body(msg.get("payload"))
            if "RER-External-prd authentication" not in body_text:
                continue

            match = re.search(r"verification code (\d{6})", body_text)
            if match:
                return match.group(1)

        log.warning("MFA email not found. Retrying in %s seconds.", wait_between_retries)
        sleep(wait_between_retries)

    raise TimeoutError(f"Failed to retrieve MFA code after {max_retries} attempts.")


def browser_authenticate_rer(
    email: str,
    password: str,
    token_file: Path,
    headless: bool,
    max_retries: int,
    wait_between_retries: int,
) -> dict[str, str]:
    log.info("Authenticating with RER portal as %s", email)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        page = browser.new_page()
        try:
            page.goto("https://rer.ofgem.gov.uk/Account/SignIn")
            page.wait_for_url("**/b2c_1a_rer_signin/**")

            page.fill("#signInName", email)
            page.fill("#password", password)
            page.click("button:has-text('Sign in')")
            page.wait_for_load_state("networkidle")

            login_error_message = page.query_selector("#localAccountForm > div.error.pageLevel > p")
            if login_error_message:
                raise ValueError(f"Authentication failed: {login_error_message.inner_text()}")

            button_clicked_after = datetime.datetime.now()
            page.click("#sendCode")
            page.wait_for_load_state("networkidle")

            sleep(5)
            mfa_code = retrieve_mfa_code(
                button_clicked_after=button_clicked_after,
                token_file=token_file,
                max_retries=max_retries,
                wait_between_retries=wait_between_retries,
            )

            page.fill("#verificationCode", mfa_code)
            page.click("#verifyCode")
            page.wait_for_load_state("networkidle")

            error_message = page.query_selector("div.error:nth-child(2)")
            if error_message:
                error_text = error_message.inner_text().strip()
                if error_text:
                    raise ValueError(f"MFA verification failed: {error_text}")

            page.wait_for_url("https://rer.ofgem.gov.uk/**", timeout=300000)
            cookies = page.context.cookies()
            assert  all("name" in cookie and "value" in cookie for cookie in cookies), "Unexpected cookie format - missing name or value"
            return {cookie["name"]: cookie["value"] for cookie in cookies} # type: ignore
        finally:
            browser.close()


def save_cookies(cookies: dict[str, str], cookies_file: Path) -> None:
    persistent_cookies = {key: value for key, value in cookies.items() if not key.startswith("ai_")}
    cookies_file.write_text(json.dumps(persistent_cookies, indent=2), encoding="utf-8")
    log.info("Saved %s cookies to %s", len(persistent_cookies), cookies_file)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Regenerate rer_cookies.json using the legacy RER login flow.")
    parser.add_argument("--email", default=os.getenv("RER_EMAIL"))
    parser.add_argument("--password", default=os.getenv("RER_PASSWORD"))
    parser.add_argument("--cookies-file", type=Path, default=REPO_ROOT / "rer_cookies.json")
    parser.add_argument("--gmail-token", type=Path, default=REPO_ROOT / "gmail_token.json")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--max-retries", type=int, default=5)
    parser.add_argument("--wait-between-retries", type=int, default=10)
    return parser.parse_args()


def main() -> None:
    load_dotenv(REPO_ROOT / ".env")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args()

    if not args.email:
        raise ValueError("Provide RER_EMAIL in .env or pass --email.")
    if not args.password:
        raise ValueError("Provide RER_PASSWORD in .env or pass --password.")

    cookies = browser_authenticate_rer(
        email=args.email,
        password=args.password,
        token_file=args.gmail_token,
        headless=args.headless,
        max_retries=args.max_retries,
        wait_between_retries=args.wait_between_retries,
    )
    save_cookies(cookies, args.cookies_file)


if __name__ == "__main__":
    main()
