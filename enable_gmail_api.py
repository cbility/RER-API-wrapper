"""
Enable Gmail API for your project
"""

print("=" * 80)
print("ENABLE GMAIL API")
print("=" * 80)
print()
print("You need to enable the Gmail API for your Google Cloud project.")
print()
print("Quick fix:")
print()
print("1. Click this link:")
print("   https://console.developers.google.com/apis/api/gmail.googleapis.com/overview?project=916881218171")
print()
print("2. Click the blue 'ENABLE' button")
print()
print("3. Wait 1-2 minutes for it to propagate")
print()
print("4. Run: python retrieve_gmail_messages_api.py")
print()
print("=" * 80)
print()
input("Press Enter once you've enabled the Gmail API...")
print()
print("Testing now...")

import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

creds = Credentials.from_authorized_user_file('gmail_token.json', ['https://mail.google.com/'])
service = build('gmail', 'v1', credentials=creds)

try:
    # Try to get profile to test API access
    profile = service.users().getProfile(userId='me').execute()
    print(f"✓ Gmail API is working!")
    print(f"✓ Email: {profile.get('emailAddress')}")
    print(f"✓ Total messages: {profile.get('messagesTotal')}")
    print()
    print("=" * 80)
    print("SUCCESS! You can now use retrieve_gmail_messages_api.py")
    print("=" * 80)
except Exception as e:
    print(f"✗ Error: {e}")
    print()
    print("If you just enabled it, wait a few minutes and try again.")
