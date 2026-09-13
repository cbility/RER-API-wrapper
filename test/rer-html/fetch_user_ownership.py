"""Fetch and save HTML from GET /User/Ownership."""

import os
from _auth import get_client

OUTPUT = os.path.join(os.path.dirname(__file__), "user_ownership.html")

client = get_client()
response = client.session.get(client.base_url + "User/Ownership")
response.raise_for_status()

with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write(response.text)

print(f"Saved HTML to {OUTPUT}")
print(f"Status: {response.status_code}")
