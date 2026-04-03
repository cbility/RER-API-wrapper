"""
Gmail message retrieval using Gmail API (OAuth2).
This is Google's recommended approach and works reliably.
"""

import os
import base64
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv
import logging

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from email.utils import parsedate_to_datetime

load_dotenv()

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def load_oauth2_credentials(token_file: str = "gmail_token.json"):
    """Load and refresh OAuth2 credentials."""
    if not os.path.exists(token_file):
        raise FileNotFoundError(
            f"{token_file} not found. Run: python setup_gmail_oauth.py"
        )
    
    creds = Credentials.from_authorized_user_file(token_file, ['https://mail.google.com/'])
    
    # Refresh if expired
    if creds and creds.expired and creds.refresh_token:
        log.info("Refreshing OAuth2 credentials...")
        creds.refresh(Request())
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
        log.info("✓ Credentials refreshed")
    
    return creds


def get_gmail_messages(since_date: datetime, max_messages: int = 100) -> List[Dict[str, Any]]:
    """
    Retrieve Gmail messages since a specific date using Gmail API.
    
    Args:
        since_date: DateTime object specifying the earliest date to retrieve messages from
        max_messages: Maximum number of messages to retrieve (default: 100)
    
    Returns:
        List of dictionaries containing:
            - time_received: datetime when email was received
            - status: read/unread status
            - subject: email subject
            - from: sender email address
            - to: recipient email address(es)
            - body: email content (plain text)
            - body_html: email content (HTML if available)
            - message_id: Gmail message ID
    
    Prerequisites:
        Run: python setup_gmail_oauth.py (one-time setup)
    """
    # Load credentials
    creds = load_oauth2_credentials()
    
    # Build Gmail API service
    log.info("Connecting to Gmail API...")
    service = build('gmail', 'v1', credentials=creds)
    
    # Format date for Gmail query (YYYY/MM/DD)
    date_str = since_date.strftime("%Y/%m/%d")
    
    # Search for messages
    query = f'after:{date_str}'
    log.info(f"Searching for messages {query}...")
    
    try:
        # Get list of message IDs
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_messages
        ).execute()
        
        message_list = results.get('messages', [])
        
        if not message_list:
            log.info("No messages found")
            return []
        
        log.info(f"Found {len(message_list)} messages")
        
        # Fetch full message details
        messages = []
        for idx, msg_ref in enumerate(message_list, 1):
            log.info(f"Processing message {idx}/{len(message_list)}...")
            
            msg = service.users().messages().get(
                userId='me',
                id=msg_ref['id'],
                format='full'
            ).execute()
            
            # Parse message
            parsed = parse_gmail_message(msg)
            messages.append(parsed)
        
        log.info(f"Successfully retrieved {len(messages)} messages")
        return messages
        
    except Exception as e:
        log.error(f"Error retrieving messages: {e}")
        raise


def parse_gmail_message(msg: dict) -> Dict[str, Any]:
    """Parse Gmail API message into structured format."""
    payload = msg.get('payload', {})
    headers = payload.get('headers', [])
    
    # Extract headers
    subject = get_header(headers, 'Subject')
    from_addr = get_header(headers, 'From')
    to_addr = get_header(headers, 'To')
    date_str = get_header(headers, 'Date')
    
    # Parse date
    try:
        time_received = parsedate_to_datetime(date_str) if date_str else datetime.now()
    except:
        time_received = datetime.now()
    
    # Get read/unread status
    labels = msg.get('labelIds', [])
    status = 'unread' if 'UNREAD' in labels else 'read'
    
    # Extract body
    body_plain = ''
    body_html = ''
    
    if 'parts' in payload:
        # Multipart message
        for part in payload['parts']:
            body_plain_part, body_html_part = extract_body_from_part(part)
            if body_plain_part:
                body_plain += body_plain_part
            if body_html_part:
                body_html += body_html_part
    else:
        # Single part message
        body_plain, body_html = extract_body_from_part(payload)
    
    return {
        'message_id': msg['id'],
        'time_received': time_received,
        'status': status,
        'subject': subject,
        'from': from_addr,
        'to': to_addr,
        'body': body_plain,
        'body_html': body_html
    }


def get_header(headers: list, name: str) -> str:
    """Get header value by name."""
    for header in headers:
        if header['name'].lower() == name.lower():
            return header['value']
    return ''


def extract_body_from_part(part: dict) -> tuple:
    """Extract plain text and HTML body from message part."""
    body_plain = ''
    body_html = ''
    
    mime_type = part.get('mimeType', '')
    
    if mime_type == 'text/plain':
        body_data = part.get('body', {}).get('data', '')
        if body_data:
            body_plain = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
    
    elif mime_type == 'text/html':
        body_data = part.get('body', {}).get('data', '')
        if body_data:
            body_html = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
    
    elif mime_type.startswith('multipart/'):
        # Recursively process nested parts
        for subpart in part.get('parts', []):
            plain, html = extract_body_from_part(subpart)
            if plain:
                body_plain += plain
            if html:
                body_html += html
    
    return body_plain, body_html


if __name__ == "__main__":
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
            
    except FileNotFoundError as e:
        log.error(str(e))
        log.error("Please run: python setup_gmail_oauth.py")
    except Exception as e:
        log.error(f"Failed to retrieve messages: {e}")
