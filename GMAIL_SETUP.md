# Gmail Message Retrieval - Setup Instructions

## Authentication Setup

Gmail no longer supports regular username/password authentication for IMAP access. You need to use an **App Password**.

### Steps to Create a Gmail App Password:

1. **Enable 2-Step Verification** (if not already enabled):
   - Go to [Google Account Security](https://myaccount.google.com/security)
   - Under "How you sign in to Google", select "2-Step Verification"
   - Follow the prompts to enable it

2. **Create an App Password**:
   - Go to [App Passwords](https://myaccount.google.com/apppasswords)
   - Select "Mail" as the app
   - Select "Windows Computer" (or your device type)
   - Click "Generate"
   - Copy the 16-character password (it will look like: `xxxx xxxx xxxx xxxx`)

3. **Update your .env file**:
   ```env
   GMAIL_EMAIL=your.email@gmail.com
   GMAIL_PASSWORD=xxxxxxxxxxxxxxxx
   ```
   Replace `xxxxxxxxxxxxxxxx` with the 16-character App Password (remove spaces)

## Usage

```python
from retrieve_gmail_messages import get_gmail_messages
from datetime import datetime, timedelta

# Get messages from the last 7 days
since_date = datetime.now() - timedelta(days=7)
messages = get_gmail_messages(since_date, max_messages=50)

# Access message data
for msg in messages:
    print(f"From: {msg['from']}")
    print(f"Subject: {msg['subject']}")
    print(f"Received: {msg['time_received']}")
    print(f"Status: {msg['status']}")  # "read" or "unread"
    print(f"Body: {msg['body']}")
    print(f"HTML Body: {msg['body_html']}")
```

## Function Returns

Each message is a dictionary with:
- `time_received`: DateTime when email was received
- `status`: "read" or "unread"
- `subject`: Email subject line
- `from`: Sender email address
- `to`: Recipient email address(es)
- `body`: Plain text email content
- `body_html`: HTML email content (if available)

## Testing

Run the script directly to test with the last 10 messages from the past 7 days:

```bash
python retrieve_gmail_messages.py
```

## Persistent Authentication

The IMAP connection uses your App Password for authentication. As long as:
1. Your App Password remains valid in the .env file
2. Your Google account's 2-Step Verification stays enabled
3. The App Password is not revoked

The authentication will work persistently without requiring any manual intervention.

## Troubleshooting

**Error: Invalid credentials**
- Make sure you're using an App Password, not your regular Gmail password
- Verify the App Password is correctly copied (no spaces)
- Check that 2-Step Verification is enabled on your account

**Error: Connection refused**
- Check your internet connection
- Verify Gmail IMAP is enabled: Settings → Forwarding and POP/IMAP → Enable IMAP

**No messages returned**
- Check the `since_date` parameter - make sure you have emails in that timeframe
- Try increasing `max_messages` parameter
