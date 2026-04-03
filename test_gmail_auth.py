"""
Diagnostic script to test Gmail authentication.
This helps verify your App Password is configured correctly.
"""

import os
from dotenv import load_dotenv
import imaplib

load_dotenv()

gmail_user = os.getenv("GMAIL_EMAIL")
gmail_password = os.getenv("GMAIL_PASSWORD")

print("=" * 80)
print("Gmail Authentication Diagnostic")
print("=" * 80)
print()

# Check if credentials are loaded
print("1. Checking environment variables...")
if not gmail_user:
    print("   ✗ GMAIL_EMAIL is not set in .env file")
else:
    print(f"   ✓ GMAIL_EMAIL: {gmail_user}")

if not gmail_password:
    print("   ✗ GMAIL_PASSWORD is not set in .env file")
else:
    # Show masked password
    masked = gmail_password[:2] + "*" * (len(gmail_password) - 4) + gmail_password[-2:]
    print(f"   ✓ GMAIL_PASSWORD: {masked} (length: {len(gmail_password)} chars)")
    
    # Check for common issues
    if " " in gmail_password:
        print("   ⚠ WARNING: Password contains spaces! Remove all spaces from App Password")
    if len(gmail_password) != 16:
        print(f"   ⚠ WARNING: App Password should be exactly 16 characters, yours is {len(gmail_password)}")

print()

if not gmail_user or not gmail_password:
    print("Cannot test authentication - credentials missing")
    exit(1)

# Test authentication
print("2. Testing IMAP authentication...")
try:
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    print("   ✓ Connected to imap.gmail.com")
    
    mail.login(gmail_user, gmail_password)
    print("   ✓ Authentication successful!")
    
    # Get mailbox info
    status, messages = mail.select("INBOX")
    if status == "OK":
        msg_count = messages[0].decode()
        print(f"   ✓ Mailbox access granted - {msg_count} messages in INBOX")
    
    mail.logout()
    print()
    print("=" * 80)
    print("SUCCESS! Your Gmail credentials are configured correctly.")
    print("=" * 80)
    
except imaplib.IMAP4.error as e:
    print(f"   ✗ Authentication failed: {e}")
    print()
    print("Troubleshooting steps:")
    print("1. Verify you created an App Password (not your regular Gmail password)")
    print("2. Go to: https://myaccount.google.com/apppasswords")
    print("3. Create a new App Password for 'Mail'")
    print("4. Copy the 16-character password (remove all spaces)")
    print("5. Update .env file:")
    print(f"   GMAIL_EMAIL={gmail_user}")
    print("   GMAIL_PASSWORD=your16charpassword")
    print()
    print("6. If App Password still doesn't work, check:")
    print("   - 2-Step Verification is enabled on your Google account")
    print("   - IMAP is enabled: Gmail Settings → Forwarding and POP/IMAP → Enable IMAP")
    print("   - Try generating a fresh App Password")
    
except Exception as e:
    print(f"   ✗ Connection error: {e}")
    print()
    print("Check your network connection and firewall settings")
