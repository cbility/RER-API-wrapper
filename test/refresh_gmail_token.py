"""Manually refresh Gmail OAuth token.

Run from the repository root:
    uv run python test/refresh_gmail_token.py

This will open a browser for authentication and save the token to gmail_token.json
"""
import os
import json
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

REPO_ROOT = Path(__file__).resolve().parents[1]
GMAIL_CREDS_FILE = REPO_ROOT / "gmail_credentials.json"
GMAIL_TOKEN_FILE = REPO_ROOT / "gmail_token.json"
GMAIL_SCOPES = ["https://mail.google.com/"]


def main():
    creds = None
    
    # Load existing token if available
    if GMAIL_TOKEN_FILE.exists():
        with open(GMAIL_TOKEN_FILE) as f:
            creds = Credentials.from_authorized_user_info(json.load(f), GMAIL_SCOPES)
    
    # Refresh if possible, otherwise re-authenticate
    if creds and creds.expired and creds.refresh_token:
        print("Refreshing existing token...")
        try:
            creds.refresh(Request())
            print("✓ Token refreshed successfully!")
        except Exception as e:
            print(f"✗ Token refresh failed: {e}")
            print("Will re-authenticate...")
            creds = None
    
    if not creds or not creds.valid:
        if not GMAIL_CREDS_FILE.exists():
            print(f"✗ Gmail credentials file not found: {GMAIL_CREDS_FILE}")
            print("\nYou need to:")
            print("1. Go to https://console.cloud.google.com/")
            print("2. Create a project and enable Gmail API")
            print("3. Create OAuth 2.0 credentials (Desktop app)")
            print("4. Download the JSON and save it as gmail_credentials.json")
            return
        
        print("\n" + "="*60)
        print("Opening browser for Gmail authentication...")
        print("="*60)
        print("\nPlease complete the authentication in your browser.")
        print("This will grant access to read emails for MFA codes.\n")
        
        flow = InstalledAppFlow.from_client_secrets_file(
            GMAIL_CREDS_FILE, GMAIL_SCOPES
        )
        creds = flow.run_local_server(port=0, open_browser=True)
        print("\n✓ Authentication successful!")
    
    # Save the token
    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
        "expiry": creds.expiry.isoformat() if creds.expiry else None,
    }
    
    with open(GMAIL_TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)
    
    print(f"✓ Token saved to {GMAIL_TOKEN_FILE}")
    print(f"  Expires: {creds.expiry}")
    print(f"  Has refresh token: {bool(creds.refresh_token)}")


if __name__ == "__main__":
    main()
