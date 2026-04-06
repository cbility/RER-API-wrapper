"""Fetch and save HTML from GET /Organisations/{organisationId}/Tasks/StationDeclarations.

Gets the first organisation ID from the user dashboard automatically.
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from _auth import get_wrapper
from bs4 import BeautifulSoup

OUTPUT = os.path.join(os.path.dirname(__file__), 'organisation_station_declarations.html')

wrapper = get_wrapper()

dashboard = wrapper.session.get(wrapper.base_url + 'User')
dashboard.raise_for_status()
soup = BeautifulSoup(dashboard.text, 'html.parser')

org_links = soup.find_all('a', href=lambda h: h and '/Organisations/GEN' in h)
if not org_links:
    print("No organisation links found on dashboard.")
    sys.exit(1)

org_id = org_links[0]['href'].split('/Organisations/')[-1].split('/')[0]
print(f"Using organisation ID: {org_id}")

response = wrapper.session.get(wrapper.base_url + f'Organisations/{org_id}/Tasks/StationDeclarations')
response.raise_for_status()

with open(OUTPUT, 'w', encoding='utf-8') as f:
    f.write(response.text)

print(f"Saved HTML to {OUTPUT}")
print(f"Status: {response.status_code}")
