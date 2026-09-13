"""Fetch and save HTML from GET /User/Notifications."""

import os
from _auth import get_client

OUTPUT = os.path.join(os.path.dirname(__file__), "user_notifications.html")

client = get_client()
response = client.session.get(client.base_url + "User/Notifications")
response.raise_for_status()

with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write(response.text)

print(f"Saved HTML to {OUTPUT}")
print(f"Status: {response.status_code}")
