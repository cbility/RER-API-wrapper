"""Fetch and save HTML from certificate-related endpoints for org GEN0202802."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from _auth import get_wrapper

ORG_ID = "GEN0202802"
BASE_DIR = os.path.dirname(__file__)

wrapper = get_wrapper()

pages = [
    ("certificates_overview", f"Organisations/{ORG_ID}/Certificates"),
    ("certificates_rego_breakdown", f"Organisations/{ORG_ID}/Certificates/REGO/Breakdown"),
    ("certificates_roc_breakdown", f"Organisations/{ORG_ID}/Certificates/ROC/Breakdown"),
    ("certificates_rego_history", f"Organisations/{ORG_ID}/Certificates/REGO/History?fromDate=05%2F01%2F2024%2000%3A00%3A00%20%2B01%3A00&toDate=04%2F07%2F2026%2012%3A14%3A27%20%2B01%3A00"),
    ("certificates_roc_history", f"Organisations/{ORG_ID}/Certificates/ROC/History?fromDate=05%2F01%2F2024%2000%3A00%3A00%20%2B01%3A00&toDate=04%2F07%2F2026%2012%3A16%3A36%20%2B01%3A00"),
]

for name, path in pages:
    print(f"Fetching {name}...")
    response = wrapper.session.get(wrapper.base_url + path)
    response.raise_for_status()
    out = os.path.join(BASE_DIR, f"{name}.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(response.text)
    print(f"  Saved to {out} ({len(response.text)} chars)")
