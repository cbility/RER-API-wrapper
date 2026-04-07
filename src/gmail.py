# region imports

import os
import logging
from datetime import datetime
from typing import List, TypedDict, NotRequired

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# endregion imports

# region config

logger = logging.getLogger(__name__)

def get_no_token_error_message(token_file_path: str) -> str:
    return f"""
            {'='*80}"
            ERROR: {token_file_path} not found!"
            {'='*80}"
            Gmail API requires OAuth2 authentication. Follow these steps:"
            1. CREATE OAUTH2 CREDENTIALS:"
               → Go to: https://console.cloud.google.com/apis/credentials"
               → Click '+ CREATE CREDENTIALS' → 'OAuth client ID'"
               → Application type: 'Desktop app'"
               → Click 'CREATE' and download JSON"
               → Save as 'gmail_credentials.json' in this directory"
            2. ENABLE GMAIL API:"
               → https://console.cloud.google.com/apis/library/gmail.googleapis.com"
               → Click 'ENABLE'"
            3. ADD TEST USER:"
               → https://console.cloud.google.com/apis/credentials/consent"
               → Under 'Test users', click '+ ADD USERS'"
               → Add your Gmail address"
            4. RUN OAUTH FLOW:"
               → Run this Python code:"
                 from google_auth_oauthlib.flow import InstalledAppFlow"
                 flow = InstalledAppFlow.from_client_secrets_file("
                     'gmail_credentials.json',"
                     ['https://mail.google.com/']"
                 )"
                 creds = flow.run_local_server(port=0)"
                 with open('{token_file_path}', 'w') as f:"
                     f.write(creds.to_json())"
               → A browser will open for authorization"
               → Click 'Continue' or 'Advanced' → 'Go to [app] (unsafe)'"
               → Authorize access"
            Once {token_file_path} is created, this function will work persistently."
            {'='*80}"
            """
# endregion config
# region types

class GmailMessageBody(TypedDict):
    """Body of a Gmail message part."""
    data: str  # Base64-encoded content
    size: int
    attachmentId: NotRequired[str]  # Only for attachments

class GmailMessageHeader(TypedDict):
    """Gmail message header (e.g., Subject, From, To, Date)."""
    name: str
    value: str


class GmailMessagePart(TypedDict, total=False):
    """Part of a Gmail message (body, attachments, etc.)."""
    partId: str
    mimeType: str
    filename: str
    headers: List[GmailMessageHeader]
    body: GmailMessageBody 
    parts: List['GmailMessagePart']  # Nested parts for multipart messages


class GmailMessagePayload(TypedDict, total=False):
    """Payload containing the message content and structure."""
    partId: str
    mimeType: str
    filename: str
    headers: List[GmailMessageHeader]
    body: GmailMessageBody
    parts: List[GmailMessagePart]


class GmailMessage(TypedDict):
    """
    Gmail API message object.
    See: https://developers.google.com/gmail/api/reference/rest/v1/users.messages#Message
    """
    id: str
    threadId: str
    labelIds: NotRequired[List[str]]
    snippet: NotRequired[str]
    payload: NotRequired[GmailMessagePayload]
    sizeEstimate: NotRequired[int]
    historyId: NotRequired[str]
    internalDate: NotRequired[str]
    raw: NotRequired[str]

# endregion types

# region main

def get_gmail_messages(since_date: datetime, max_messages: int = 100, token_file: str = "../gmail_token.json") -> List[GmailMessage]:
    """
    Retrieve Gmail messages since a specific date.
    
    Args:
        since_date: DateTime object specifying the earliest date to retrieve messages from
        max_messages: Maximum number of messages to retrieve (default: 100)
        token_file: Path to OAuth2 token file (default: ../gmail_token.json)
    
    Returns:
        List of raw Gmail API message objects
        See: https://developers.google.com/gmail/api/reference/rest/v1/users.messages#Message
    
    Setup:
        If gmail_token.json doesn't exist, run: python setup_gmail_oauth.py
    """
    token_file_path = os.path.join(os.path.dirname(__file__), token_file)
    # Check token file exists
    if not os.path.exists(token_file_path):
        raise FileNotFoundError(
            get_no_token_error_message(token_file_path)
        )
    
    # Load credentials
    creds = Credentials.from_authorized_user_file(token_file_path, ['https://mail.google.com/'])
    
    # Refresh if expired
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_file_path, 'w') as token:
            token.write(creds.to_json())
    
    # Build Gmail API service
    service = build('gmail', 'v1', credentials=creds)
    
    # Search for messages
    query = f'after:{since_date.strftime("%Y/%m/%d")}'
    results = service.users().messages().list(userId='me', q=query, maxResults=max_messages).execute()
    
    message_ids = results.get('messages', [])
    if not message_ids:
        logger.debug("No messages found")
        return []
    
    logger.debug(f"Retrieved {len(message_ids)} message IDs")
    
    # Fetch full message details
    messages = []
    for msg_ref in message_ids:
        msg = service.users().messages().get(userId='me', id=msg_ref['id'], format='full').execute()
        messages.append(msg)
    
    # Log received times at debug level
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Message received times:")
        for idx, msg in enumerate(messages, 1):
            internal_date = msg.get('internalDate', 'Unknown')
            # internalDate is epoch milliseconds
            if internal_date != 'Unknown':
                dt = datetime.fromtimestamp(int(internal_date) / 1000)
                logger.debug(f"  [{idx}] {msg['id']}: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                logger.debug(f"  [{idx}] {msg['id']}: Unknown")
    
    return messages

# endregion main
# region testing
if __name__ == "__main__":
    from datetime import timedelta
    
    # Enable debug logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Get messages from the last 7 days
    since = datetime.now() - timedelta(days=7)
    
    try:
        messages = get_gmail_messages(since, max_messages=5)
        
        print(f"\n{'='*80}")
        print(f"Retrieved {len(messages)} messages since {since.strftime('%Y-%m-%d')}")
        print(f"{'='*80}\n")
        
        for idx, msg in enumerate(messages, 1):
            print(f"Message {idx}:")
            print(f"  ID: {msg.get('id')}")
            print(f"  Thread ID: {msg.get('threadId')}")
            print(f"  Labels: {msg.get('labelIds', [])}")
            print(f"  Snippet: {msg.get('snippet', '')[:100]}...")
            print(f"  {'='*80}\n")
            
    except FileNotFoundError as e:
        print(str(e))
    except Exception as e:
        print(f"Error: {e}")

# endregion