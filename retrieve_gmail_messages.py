import imaplib
import email
from email.header import decode_header
from datetime import datetime
from typing import List, Dict, Any, Optional
import os
from dotenv import load_dotenv
import logging
import socket

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    OAUTH2_AVAILABLE = True
except ImportError:
    OAUTH2_AVAILABLE = False

load_dotenv()

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def load_oauth2_credentials(token_file: str = "gmail_token.json") -> Optional[Credentials]:
    """
    Load OAuth2 credentials from token file.
    
    Returns:
        Credentials object if available and valid, None otherwise
    """
    if not OAUTH2_AVAILABLE:
        return None
    
    if not os.path.exists(token_file):
        return None
    
    try:
        creds = Credentials.from_authorized_user_file(token_file, ['https://mail.google.com/'])
        
        # Refresh if expired
        if creds and creds.expired and creds.refresh_token:
            log.info("Refreshing OAuth2 credentials...")
            creds.refresh(Request())
            # Save refreshed credentials
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
            log.info("✓ Credentials refreshed")
        
        if creds and creds.valid:
            return creds
    except Exception as e:
        log.warning(f"Could not load OAuth2 credentials: {e}")
    
    return None


def generate_oauth2_string(email: str, access_token: str) -> str:
    """Generate OAuth2 authentication string for IMAP."""
    return f'user={email}\x01auth=Bearer {access_token}\x01\x01'


def connect_gmail_imap(gmail_user: str, gmail_password: str = None, use_oauth2: bool = True) -> imaplib.IMAP4_SSL:
    """
    Connect to Gmail IMAP with OAuth2 or App Password.
    
    Args:
        gmail_user: Gmail email address
        gmail_password: App Password (if not using OAuth2)
        use_oauth2: Try OAuth2 first if available
    
    Returns:
        Authenticated IMAP connection
    """
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    
    # Try OAuth2 first if available
    if use_oauth2:
        creds = load_oauth2_credentials()
        if creds:
            try:
                log.info("Authenticating with OAuth2...")
                auth_string = generate_oauth2_string(gmail_user, creds.token)
                mail.authenticate('XOAUTH2', lambda x: auth_string)
                log.info("✓ OAuth2 authentication successful")
                return mail
            except Exception as e:
                log.warning(f"OAuth2 authentication failed: {e}")
                log.info("Falling back to App Password...")
    
    # Fall back to App Password
    if not gmail_password:
        raise ValueError("No OAuth2 credentials and no GMAIL_PASSWORD provided")
    
    log.info("Authenticating with App Password...")
    mail.login(gmail_user, gmail_password)
    log.info("✓ App Password authentication successful")
    return mail


def test_network_connectivity(host: str = "imap.gmail.com", port: int = 993) -> bool:
    """
    Test network connectivity to Gmail IMAP server.
    
    Args:
        host: IMAP server hostname
        port: IMAP SSL port (default: 993)
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        log.info(f"Testing DNS resolution for {host}...")
        ip_address = socket.gethostbyname(host)
        log.info(f"✓ DNS resolved: {host} -> {ip_address}")
        
        log.info(f"Testing TCP connection to {host}:{port}...")
        sock = socket.create_connection((host, port), timeout=10)
        sock.close()
        log.info(f"✓ TCP connection successful to {host}:{port}")
        
        return True
    except socket.gaierror as e:
        log.error(f"✗ DNS resolution failed: {e}")
        log.error("Possible causes:")
        log.error("  - No internet connection")
        log.error("  - DNS server not responding")
        log.error("  - Corporate proxy/firewall blocking DNS")
        log.error("\nTroubleshooting steps:")
        log.error("  1. Check your internet connection")
        log.error("  2. Try: ping 8.8.8.8 (test basic connectivity)")
        log.error("  3. Try: nslookup imap.gmail.com (test DNS)")
        log.error("  4. Check if you're behind a corporate proxy/VPN")
        return False
    except socket.timeout as e:
        log.error(f"✗ Connection timeout: {e}")
        log.error("Possible causes:")
        log.error("  - Firewall blocking port 993")
        log.error("  - Network connectivity issues")
        return False
    except Exception as e:
        log.error(f"✗ Connection test failed: {e}")
        return False


def get_gmail_messages(since_date: datetime, max_messages: int = 100, use_oauth2: bool = True) -> List[Dict[str, Any]]:
    """
    Retrieve Gmail messages since a specific date using IMAP.
    
    Args:
        since_date: DateTime object specifying the earliest date to retrieve messages from
        max_messages: Maximum number of messages to retrieve (default: 100)
        use_oauth2: Try OAuth2 authentication first (recommended)
    
    Returns:
        List of dictionaries containing:
            - time_received: datetime when email was received
            - status: read/unread status
            - subject: email subject
            - from: sender email address
            - to: recipient email address(es)
            - body: email content (plain text)
            - body_html: email content (HTML if available)
    
    Authentication Methods (in order of preference):
    1. OAuth2 (if gmail_token.json exists) - Most reliable, no password needed
       Run: python setup_gmail_oauth.py to set this up
    
    2. App Password (if GMAIL_PASSWORD in .env) - Backup method
       Requires 2-Step Verification and App Password from:
       https://myaccount.google.com/apppasswords
    
    Note: OAuth2 is strongly recommended as it's more reliable and secure.
    """
    gmail_user = os.getenv("GMAIL_EMAIL")
    gmail_password = os.getenv("GMAIL_PASSWORD")
    
    if not gmail_user:
        raise ValueError("GMAIL_EMAIL must be set in .env file")
    
    # Check if OAuth2 is available
    oauth2_available = os.path.exists("gmail_token.json") and OAUTH2_AVAILABLE
    if not oauth2_available and not gmail_password:
        raise ValueError(
            "No authentication method available!\n"
            "Either:\n"
            "  1. Run: python setup_gmail_oauth.py (recommended)\n"
            "  2. Set GMAIL_PASSWORD in .env file with an App Password"
        )
    
    # Test network connectivity first
    log.info("Running connectivity diagnostics...")
    if not test_network_connectivity():
        raise ConnectionError("Cannot connect to Gmail IMAP server. See error messages above for troubleshooting steps.")
    
    messages = []
    
    try:
        # Connect to Gmail IMAP server
        log.info(f"Connecting to Gmail IMAP server for {gmail_user}...")
        mail = connect_gmail_imap(gmail_user, gmail_password, use_oauth2)
        
        # Select mailbox (INBOX)
        mail.select("inbox")
        
        # Format date for IMAP search (DD-MMM-YYYY format)
        date_str = since_date.strftime("%d-%b-%Y")
        
        # Search for messages since the specified date
        log.info(f"Searching for messages since {date_str}...")
        status, message_ids = mail.search(None, f'SINCE {date_str}')
        
        if status != "OK":
            log.error("Failed to search messages")
            return messages
        
        # Get list of message IDs
        message_id_list = message_ids[0].split()
        total_messages = len(message_id_list)
        log.info(f"Found {total_messages} messages")
        
        # Limit the number of messages to retrieve
        message_id_list = message_id_list[-max_messages:] if len(message_id_list) > max_messages else message_id_list
        
        # Fetch each message
        for idx, msg_id in enumerate(message_id_list, 1):
            log.info(f"Processing message {idx}/{len(message_id_list)}...")
            
            # Fetch the message
            status, msg_data = mail.fetch(msg_id, "(RFC822 FLAGS)")
            
            if status != "OK":
                log.warning(f"Failed to fetch message {msg_id}")
                continue
            
            # Parse the email
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Get message metadata
                    subject = decode_email_header(msg["Subject"])
                    from_addr = decode_email_header(msg["From"])
                    to_addr = decode_email_header(msg["To"])
                    date_str = msg["Date"]
                    
                    # Parse date
                    time_received = email.utils.parsedate_to_datetime(date_str)
                    
                    # Get read/unread status
                    flags_match = str(msg_data[0]).split("FLAGS")[1] if len(msg_data) > 0 else ""
                    is_seen = "\\Seen" in flags_match
                    status_str = "read" if is_seen else "unread"
                    
                    # Extract email body
                    body_plain = ""
                    body_html = ""
                    
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition"))
                            
                            # Skip attachments
                            if "attachment" in content_disposition:
                                continue
                            
                            try:
                                body_content = part.get_payload(decode=True)
                                if body_content:
                                    if content_type == "text/plain":
                                        body_plain = body_content.decode('utf-8', errors='ignore')
                                    elif content_type == "text/html":
                                        body_html = body_content.decode('utf-8', errors='ignore')
                            except Exception as e:
                                log.warning(f"Error decoding message part: {e}")
                    else:
                        # Not multipart - get payload
                        try:
                            body_content = msg.get_payload(decode=True)
                            if body_content:
                                content_type = msg.get_content_type()
                                if content_type == "text/plain":
                                    body_plain = body_content.decode('utf-8', errors='ignore')
                                elif content_type == "text/html":
                                    body_html = body_content.decode('utf-8', errors='ignore')
                        except Exception as e:
                            log.warning(f"Error decoding message body: {e}")
                    
                    # Add to results
                    messages.append({
                        "time_received": time_received,
                        "status": status_str,
                        "subject": subject,
                        "from": from_addr,
                        "to": to_addr,
                        "body": body_plain,
                        "body_html": body_html
                    })
        
        # Logout
        mail.close()
        mail.logout()
        log.info(f"Successfully retrieved {len(messages)} messages")
        
    except imaplib.IMAP4.error as e:
        log.error(f"IMAP error: {e}")
        log.error("If you're using a regular password, you need to use an App Password instead.")
        log.error("See function docstring for instructions on creating an App Password.")
        raise
    except socket.gaierror as e:
        log.error(f"DNS resolution error: {e}")
        log.error("Cannot resolve imap.gmail.com - check your internet connection and DNS settings")
        raise
    except socket.error as e:
        log.error(f"Network connection error: {e}")
        log.error("Cannot connect to Gmail IMAP server - check firewall settings")
        raise
    except Exception as e:
        log.error(f"Error retrieving Gmail messages: {e}")
        raise
    
    return messages


def decode_email_header(header: str) -> str:
    """Decode email header that may contain encoded words."""
    if header is None:
        return ""
    
    decoded_parts = []
    for part, encoding in decode_header(header):
        if isinstance(part, bytes):
            decoded_parts.append(part.decode(encoding or 'utf-8', errors='ignore'))
        else:
            decoded_parts.append(part)
    
    return ''.join(decoded_parts)


if __name__ == "__main__":
    # Example usage
    from datetime import timedelta
    
    # Get messages from the last 7 days
    since = datetime.now() - timedelta(days=7)
    
    try:
        messages = get_gmail_messages(since, max_messages=10)
        
        print(f"\n{'='*80}")
        print(f"Retrieved {len(messages)} messages since {since.strftime('%Y-%m-%d')}")
        print(f"{'='*80}\n")
        
        for idx, msg in enumerate(messages, 1):
            print(f"Message {idx}:")
            print(f"  Time: {msg['time_received']}")
            print(f"  Status: {msg['status']}")
            print(f"  From: {msg['from']}")
            print(f"  Subject: {msg['subject']}")
            print(f"  Body (first 200 chars): {msg['body'][:200]}...")
            print(f"  {'='*80}\n")
            
    except Exception as e:
        log.error(f"Failed to retrieve messages: {e}")
