"""
Comprehensive Gmail authentication tester.
Tests multiple authentication methods and provides detailed diagnostics.
"""

import os
from dotenv import load_dotenv
import imaplib
import socket

load_dotenv()

gmail_user = os.getenv("GMAIL_EMAIL")
gmail_password = os.getenv("GMAIL_PASSWORD")

print("=" * 80)
print("COMPREHENSIVE GMAIL AUTHENTICATION DIAGNOSTICS")
print("=" * 80)
print()

# Step 1: Environment check
print("STEP 1: Environment Variables")
print("-" * 80)
if not gmail_user:
    print("✗ GMAIL_EMAIL is not set in .env file")
    exit(1)
else:
    print(f"✓ GMAIL_EMAIL: {gmail_user}")

if not gmail_password:
    print("✗ GMAIL_PASSWORD is not set in .env file")
    exit(1)
else:
    masked = gmail_password[:2] + "*" * (len(gmail_password) - 4) + gmail_password[-2:]
    print(f"✓ GMAIL_PASSWORD: {masked} (length: {len(gmail_password)} chars)")
    
    # Check for issues
    issues = []
    if " " in gmail_password:
        issues.append("Contains spaces (remove all spaces)")
    if len(gmail_password) != 16:
        issues.append(f"Length is {len(gmail_password)}, should be 16")
    if not gmail_password.isalnum():
        issues.append("Contains special characters (App Password should only be letters/numbers)")
    
    if issues:
        print(f"⚠ PASSWORD ISSUES: {', '.join(issues)}")
    else:
        print("✓ Password format looks correct")

print()

# Step 2: Network connectivity
print("STEP 2: Network Connectivity")
print("-" * 80)
try:
    ip = socket.gethostbyname("imap.gmail.com")
    print(f"✓ DNS resolves: imap.gmail.com → {ip}")
    
    sock = socket.create_connection(("imap.gmail.com", 993), timeout=10)
    sock.close()
    print("✓ TCP connection successful to imap.gmail.com:993")
except Exception as e:
    print(f"✗ Network error: {e}")
    exit(1)

print()

# Step 3: IMAP connection
print("STEP 3: IMAP Connection Test")
print("-" * 80)
try:
    print("Connecting to imap.gmail.com...")
    mail = imaplib.IMAP4_SSL("imap.gmail.com", port=993)
    print("✓ SSL connection established")
    
    # Try to see server capabilities before auth
    typ, data = mail.capability()
    print(f"✓ Server capabilities received")
    
except Exception as e:
    print(f"✗ Connection failed: {e}")
    exit(1)

print()

# Step 4: Authentication attempt
print("STEP 4: Authentication Test")
print("-" * 80)
print(f"Attempting login with: {gmail_user}")
print("Using password from .env file...")

try:
    response = mail.login(gmail_user, gmail_password)
    print(f"✓ AUTHENTICATION SUCCESSFUL!")
    print(f"Server response: {response}")
    
    # Test mailbox access
    print()
    print("Testing mailbox access...")
    status, messages = mail.select("INBOX")
    if status == "OK":
        msg_count = messages[0].decode()
        print(f"✓ Mailbox access granted - {msg_count} messages in INBOX")
    
    mail.logout()
    
    print()
    print("=" * 80)
    print("✓✓✓ SUCCESS! Your Gmail credentials work perfectly. ✓✓✓")
    print("=" * 80)
    print()
    print("You can now use the retrieve_gmail_messages.py script.")
    
except imaplib.IMAP4.error as e:
    error_msg = str(e)
    print(f"✗ Authentication FAILED: {error_msg}")
    print()
    print("=" * 80)
    print("TROUBLESHOOTING GUIDE")
    print("=" * 80)
    print()
    
    if "AUTHENTICATIONFAILED" in error_msg:
        print("The credentials are being rejected by Gmail.")
        print()
        print("This typically means one of the following:")
        print()
        print("1. App Password not properly generated")
        print("   → Google's App Password page (as of 2024+) looks like this:")
        print("   → https://myaccount.google.com/apppasswords")
        print("   → You should see 'App passwords' (may need to scroll)")
        print("   → Click it and follow prompts to create password")
        print("   → The interface may just have a text field to name it")
        print("   → Type 'Mail' or 'IMAP' as the name")
        print()
        print("2. IMAP not enabled in Gmail")
        print("   → Go to: https://mail.google.com/mail/u/0/#settings/fwdandpop")
        print("   → Look for 'IMAP access' section")
        print("   → Status should be 'IMAP is enabled'")
        print("   → If not, click 'Enable IMAP' and Save Changes")
        print()
        print("3. 2-Step Verification not enabled")
        print("   → Go to: https://myaccount.google.com/security")
        print("   → Find '2-Step Verification' - it must say 'On'")
        print("   → If Off, click it and enable it first")
        print()
        print("4. Less secure app access (for older accounts)")
        print("   → This setting may have been removed by Google")
        print("   → If you see it, it should be OFF (use App Password instead)")
        print()
        print("5. Account restrictions")
        print("   → Work/School accounts may block IMAP")
        print("   → Some countries/regions may have restrictions")
        print()
        print("=" * 80)
        print("ALTERNATIVE: Try OAuth2 authentication (more reliable)")
        print("=" * 80)
        print()
        print("Google prefers OAuth2 over App Passwords.")
        print("Would you like to switch to OAuth2 authentication?")
        print("OAuth2 requires a one-time browser login and then saves a token.")
        print()
        
    print()
    print("Current .env configuration to verify:")
    print(f"GMAIL_EMAIL={gmail_user}")
    print(f"GMAIL_PASSWORD={gmail_password[:4]}...{gmail_password[-4:]}")
    print()
    print("Double-check:")
    print("- App Password was copied WITHOUT spaces")
    print("- You're using App Password, not regular Gmail password")
    print("- IMAP is enabled in Gmail settings")
    print("- 2-Step Verification is enabled")
    
except Exception as e:
    print(f"✗ Unexpected error: {type(e).__name__}: {e}")
    print()
    print("This may indicate:")
    print("- Network/firewall issues")
    print("- Gmail server problems")
    print("- Python SSL/TLS issues")
