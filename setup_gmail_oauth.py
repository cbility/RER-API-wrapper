"""
OAuth2 Setup for Gmail IMAP Access

This script will:
1. Open a browser for you to authorize the application
2. Save credentials to gmail_token.json for persistent access
3. Test the connection

No need for App Passwords - this uses Google's official OAuth2 flow.
"""

import os
import pickle
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import imaplib
import base64

# Gmail IMAP scope
SCOPES = [
    'https://mail.google.com/',  # Full Gmail access
]

def get_oauth2_credentials():
    """
    Get OAuth2 credentials for Gmail.
    Creates gmail_token.json file for persistent authentication.
    """
    creds = None
    token_file = 'gmail_token.json'
    
    # Load existing credentials
    if os.path.exists(token_file):
        print(f"Found existing token file: {token_file}")
        try:
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)
            print("✓ Loaded existing credentials")
        except Exception as e:
            print(f"Could not load credentials: {e}")
    
    # Refresh or get new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired credentials...")
            try:
                creds.refresh(Request())
                print("✓ Credentials refreshed")
            except Exception as e:
                print(f"Could not refresh credentials: {e}")
                print("Will need to re-authenticate...")
                creds = None
        
        if not creds:
            # Need new credentials - user must authorize
            credentials_file = 'gmail_credentials.json'
            
            if not os.path.exists(credentials_file):
                print()
                print("=" * 80)
                print("OAUTH2 SETUP REQUIRED")
                print("=" * 80)
                print()
                print("STEP 1: Enable Gmail API")
                print("  → https://console.cloud.google.com/apis/library/gmail.googleapis.com")
                print("  → Click 'ENABLE' (if not already enabled)")
                print()
                print("STEP 2: Configure OAuth consent screen")
                print("  → https://console.cloud.google.com/apis/credentials/consent")
                print("  → User Type: External")
                print("  → Fill in app name, email, etc.")
                print("  → IMPORTANT: Under 'Test users', click '+ ADD USERS'")
                print("  → Add YOUR Gmail address as a test user")
                print("  → Save")
                print()
                print("STEP 3: Create OAuth credentials")
                print("  → https://console.cloud.google.com/apis/credentials")
                print("  → Click '+ CREATE CREDENTIALS' → 'OAuth client ID'")
                print("  → Application type: 'Desktop app'")
                print("  → Name: 'Gmail IMAP Desktop'")
                print("  → Click 'CREATE'")
                print("  → Click 'DOWNLOAD JSON'")
                print("  → Save as 'gmail_credentials.json' in this directory")
                print()
                print("=" * 80)
                print()
                input("Press Enter once you've saved gmail_credentials.json...")
                
                if not os.path.exists(credentials_file):
                    raise FileNotFoundError(
                        f"Could not find {credentials_file}. "
                        "Please download OAuth2 credentials from Google Cloud Console."
                    )
            
            print()
            print("Starting OAuth2 authorization flow...")
            print("A browser window will open for you to authorize the application.")
            print()
            
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
            print("✓ Authorization successful!")
        
        # Save credentials for future use
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
        print(f"✓ Credentials saved to {token_file}")
    
    return creds


def generate_oauth2_string(email, access_token):
    """Generate OAuth2 authentication string for IMAP."""
    import base64
    auth_string = f'user={email}\x01auth=Bearer {access_token}\x01\x01'
    return base64.b64encode(auth_string.encode('ascii')).decode('ascii')


def test_oauth2_imap(email, access_token):
    """Test OAuth2 authentication with Gmail IMAP."""
    print()
    print("Testing IMAP connection with OAuth2...")
    print(f"Email: {email}")
    
    try:
        # Connect to Gmail IMAP
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        print("✓ Connected to imap.gmail.com")
        
        # Authenticate using OAuth2
        auth_string = generate_oauth2_string(email, access_token)
        # Use the correct IMAP AUTHENTICATE command
        mail.send(b'ATAG AUTHENTICATE XOAUTH2 ' + auth_string.encode('ascii') + b'\r\n')
        response = mail.readline()
        
        if b'OK' in response:
            print("✓ OAuth2 authentication successful!")
        else:
            # Try the lambda method as backup
            print("Trying alternative authentication method...")
            mail = imaplib.IMAP4_SSL('imap.gmail.com')
            auth_bytes = f'user={email}\x01auth=Bearer {access_token}\x01\x01'.encode('ascii')
            mail.authenticate('XOAUTH2', lambda x: auth_bytes)
            print("✓ OAuth2 authentication successful!")
        
        # Test mailbox access
        status, messages = mail.select('INBOX')
        if status == 'OK':
            msg_count = messages[0].decode()
            print(f"✓ Mailbox access granted - {msg_count} messages in INBOX")
        
        mail.logout()
        
        print()
        print("=" * 80)
        print("✓✓✓ SUCCESS! OAuth2 authentication is working perfectly! ✓✓✓")
        print("=" * 80)
        print()
        print("Your credentials are saved in gmail_token.json")
        print("You can now use retrieve_gmail_messages.py with OAuth2")
        
        return True
        
    except Exception as e:
        print(f"✗ IMAP test failed: {e}")
        return False


if __name__ == "__main__":
    print()
    print("=" * 80)
    print("GMAIL OAUTH2 SETUP")
    print("=" * 80)
    print()
    
    try:
        # Get credentials
        creds = get_oauth2_credentials()
        
        # Get email from .env or prompt
        from dotenv import load_dotenv
        load_dotenv()
        
        email = os.getenv("GMAIL_EMAIL")
        if not email:
            email = input("Enter your Gmail address: ")
        
        # Test the connection
        success = test_oauth2_imap(email, creds.token)
        
        if success:
            print()
            print("Next steps:")
            print("1. Run: python retrieve_gmail_messages.py")
            print("2. The script will automatically use OAuth2 authentication")
            print("3. No need to worry about App Passwords anymore!")
        
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user")
    except Exception as e:
        print(f"\n\n✗ Setup failed: {e}")
        print("\nIf you need help, check the error message above.")
