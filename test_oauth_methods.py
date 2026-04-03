"""
Test OAuth2 token and try different IMAP authentication methods
"""

import os
import json
import imaplib
import base64
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv

load_dotenv()

# Load the token
token_file = 'gmail_token.json'
if not os.path.exists(token_file):
    print("Error: gmail_token.json not found. Run setup_gmail_oauth.py first.")
    exit(1)

print("Loading OAuth2 credentials...")
creds = Credentials.from_authorized_user_file(token_file, ['https://mail.google.com/'])

email = os.getenv("GMAIL_EMAIL")
access_token = creds.token

print(f"Email: {email}")
print(f"Access Token: {access_token[:20]}...{access_token[-20:]}")
print()

# Method 1: Standard XOAUTH2 with base64
print("=" * 80)
print("METHOD 1: XOAUTH2 with base64 encoding")
print("=" * 80)
try:
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    auth_string = f'user={email}\x01auth=Bearer {access_token}\x01\x01'
    auth_b64 = base64.b64encode(auth_string.encode('ascii')).decode('ascii')
    
    # Try using authenticate
    mail.authenticate('XOAUTH2', lambda x: auth_b64)
    print("✓ SUCCESS with Method 1!")
    
    status, messages = mail.select('INBOX')
    if status == 'OK':
        print(f"✓ Mailbox access: {messages[0].decode()} messages")
    mail.logout()
    exit(0)
except Exception as e:
    print(f"✗ Failed: {e}")

# Method 2: XOAUTH2 without base64
print()
print("=" * 80)
print("METHOD 2: XOAUTH2 without base64 encoding")
print("=" * 80)
try:
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    auth_string = f'user={email}\x01auth=Bearer {access_token}\x01\x01'
    
    mail.authenticate('XOAUTH2', lambda x: auth_string)
    print("✓ SUCCESS with Method 2!")
    
    status, messages = mail.select('INBOX')
    if status == 'OK':
        print(f"✓ Mailbox access: {messages[0].decode()} messages")
    mail.logout()
    exit(0)
except Exception as e:
    print(f"✗ Failed: {e}")

# Method 3: XOAUTH2 as bytes
print()
print("=" * 80)
print("METHOD 3: XOAUTH2 as bytes")
print("=" * 80)
try:
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    auth_string = f'user={email}\x01auth=Bearer {access_token}\x01\x01'
    auth_bytes = auth_string.encode('ascii')
    
    mail.authenticate('XOAUTH2', lambda x: auth_bytes)
    print("✓ SUCCESS with Method 3!")
    
    status, messages = mail.select('INBOX')
    if status == 'OK':
        print(f"✓ Mailbox access: {messages[0].decode()} messages")
    mail.logout()
    exit(0)
except Exception as e:
    print(f"✗ Failed: {e}")

# Method 4: Direct command
print()
print("=" * 80)
print("METHOD 4: Direct AUTHENTICATE command")
print("=" * 80)
try:
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    auth_string = f'user={email}\x01auth=Bearer {access_token}\x01\x01'
    auth_b64 = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')
    
    # Send authenticate command directly
    tag = mail._new_tag()
    command = f'{tag} AUTHENTICATE XOAUTH2 {auth_b64}'
    mail.send(command.encode('utf-8') + b'\r\n')
    
    # Read response
    while True:
        line = mail.readline()
        print(f"Response: {line}")
        if line.startswith(tag.encode()):
            if b'OK' in line:
                print("✓ SUCCESS with Method 4!")
                status, messages = mail.select('INBOX')
                if status == 'OK':
                    print(f"✓ Mailbox access: {messages[0].decode()} messages")
                mail.logout()
                exit(0)
            else:
                raise Exception(f"Authentication failed: {line}")
            break
except Exception as e:
    print(f"✗ Failed: {e}")

print()
print("=" * 80)
print("ALL METHODS FAILED")
print("=" * 80)
print()
print("This might indicate:")
print("1. The OAuth2 scope doesn't include IMAP access")
print("2. IMAP is not enabled for OAuth2 apps")
print("3. We need to use Gmail API instead of IMAP")
print()
print("Recommended: Switch to using Gmail API instead of IMAP")
