"""Fetch and save HTML from GET /User/Activity."""
import os
from _auth import get_wrapper

OUTPUT = os.path.join(os.path.dirname(__file__), 'user_activity.html')

wrapper = get_wrapper()
response = wrapper.session.get(wrapper.base_url + 'User/Activity')
response.raise_for_status()

with open(OUTPUT, 'w', encoding='utf-8') as f:
    f.write(response.text)

print(f"Saved HTML to {OUTPUT}")
print(f"Status: {response.status_code}")
