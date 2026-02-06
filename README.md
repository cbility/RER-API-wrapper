# RER API Wrapper

Python wrapper for the Ofgem Renewable Electricity Register (RER) portal.

## Installation

```bash
pip install playwright requests beautifulsoup4
playwright install chromium
```

## Quick Start

### 1. Authenticate (First Time)

```python
from auth import authenticate_rer

# Login and save cookies
cookies = authenticate_rer(
    email="your.email@example.com",
    password="your_password"
)

# You'll need to manually enter your MFA code in the browser
# Cookies are saved to rer_cookies.json for reuse
```

### 2. Make API Calls

```python
import requests
from auth import load_cookies, cookies_to_dict

# Load saved cookies
cookies = load_cookies("rer_cookies.json")
cookie_dict = cookies_to_dict(cookies)

# Make authenticated requests
session = requests.Session()
session.cookies.update(cookie_dict)

# Get user dashboard
response = session.get('https://rer.ofgem.gov.uk/User')
print(response.text)  # HTML page content
```

## Files

- `auth.py` - Authentication module using Playwright
- `openapi.yaml` - OpenAPI specification for RER endpoints
- `rer_cookies.json` - Saved authentication cookies (created after login)

## Authentication Flow

1. **Initial Login** - Use `authenticate_rer()` with browser automation
2. **MFA Verification** - Manually enter code when prompted
3. **Cookie Storage** - Session cookies saved to file
4. **Reuse Cookies** - Use saved cookies for subsequent requests
5. **Re-authenticate** - When cookies expire (usually 24+ hours)

## API Endpoints

See `openapi.yaml` for complete endpoint documentation.

### Key Endpoints:

- `GET /User` - User dashboard
- `GET /User/Activity` - User activity log
- `GET /Organisations/{id}` - Organisation details
- `GET /Organisations/{id}/Tasks/OutputData` - Output data tasks

## Example: Get Organisation Tasks

```python
import requests
from auth import load_cookies, cookies_to_dict
from bs4 import BeautifulSoup

# Setup authenticated session
cookies = load_cookies()
session = requests.Session()
session.cookies.update(cookies_to_dict(cookies))

# Get tasks page
org_id = "GEN0215941"
response = session.get(
    f'https://rer.ofgem.gov.uk/Organisations/{org_id}/Tasks/OutputData',
    params={'Statuses': 'Draft'}
)

# Parse HTML to extract data
soup = BeautifulSoup(response.text, 'html.parser')
# ... extract task information from HTML
```

## Notes

⚠️ **This is not an official API** - It's a wrapper around the HTML portal

⚠️ **MFA Required** - You must manually enter verification codes

⚠️ **HTML Parsing** - Responses are HTML pages, not JSON

⚠️ **Cookie Expiry** - Cookies typically last 24+ hours, then you need to re-authenticate

## Security

- Store credentials securely (use environment variables)
- Don't commit `rer_cookies.json` to version control
- Cookies grant full account access - treat like passwords
- Add `rer_cookies.json` to your `.gitignore`

## Limitations

- Not a true REST API (returns HTML, not JSON)
- Requires MFA for initial authentication
- Cookie-based auth (not API tokens)
- Subject to website changes breaking the wrapper
- No official support from Ofgem
