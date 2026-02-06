from playwright.sync_api import sync_playwright
import json
import os
from dotenv import load_dotenv

load_dotenv()


def authenticate_rer(email=None, password=None, cookies_file="rer_cookies.json"):
    """Authenticate with RER portal using Azure AD B2C."""
    email = email or os.getenv("RER_EMAIL")
    password = password or os.getenv("RER_PASSWORD")

    if not email or not password:
        raise ValueError("Set RER_EMAIL and RER_PASSWORD in .env")

    print(f"Authenticating as {email}...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # Navigate and wait for Azure B2C login
        print("Navigating to sign-in page...")
        page.goto("https://rer.ofgem.gov.uk/Account/SignIn")
        page.wait_for_url("**/b2c_1a_rer_signin/**")

        # Fill login form
        print("Filling credentials...")
        page.fill("#signInName", email)
        page.fill("#password", password)
        page.click("button:has-text('Sign in')")

        # Manual MFA step
        print("\n" + "=" * 60)
        print("COMPLETE MFA IN THE BROWSER")
        print("Enter your SMS/phone code and click Continue")
        print("=" * 60 + "\n")

        # Wait for redirect back to RER
        print("Waiting for MFA completion...")

        complete_mfa()

        page.wait_for_url("https://rer.ofgem.gov.uk/**", timeout=300000)
        print("Authentication successful!")

        # Save cookies
        cookies = page.context.cookies()
        with open(cookies_file, "w") as f:
            json.dump(cookies, f, indent=2)
        print(f"Cookies saved to {cookies_file}")

        browser.close()
        return cookies


def complete_mfa():
    """Placeholder for MFA completion instructions."""
    print("\n" + "=" * 60)
    print("COMPLETE MFA IN THE BROWSER")
    print("Enter your SMS/phone code and click Continue")
    print("=" * 60 + "\n")


def load_cookies(cookies_file="rer_cookies.json"):
    """Load saved cookies."""
    try:
        with open(cookies_file) as f:
            return json.load(f)
    except FileNotFoundError:  # TODO:
        return None


def cookies_to_dict(cookies):
    """Convert Playwright cookies to requests format."""
    return {c["name"]: c["value"] for c in cookies}


if __name__ == "__main__":
    cookies = load_cookies()

    if not cookies:
        print("No cookies found, authenticating...")
        cookies = authenticate_rer()
    else:
        print("Using saved cookies")

    cookie_dict = cookies_to_dict(cookies)
    print(f"\nReady: {len(cookie_dict)} cookies loaded")

    # Use with requests:
    # import requests
    # requests.get("https://rer.ofgem.gov.uk/User", cookies=cookie_dict)
