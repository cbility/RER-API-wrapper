# RER API Wrapper

Python wrapper for the Ofgem Renewable Electricity Register (RER) portal API. Provides a REST API that wraps the site's native HTML API and accepts and returns JSON objects. Also provides an OpenAPI schema for the wrapper.

## Installation

```bash
uv sync
```

## Getting started

To use the API you will need to authenticate with the RER portal and provide the cookies from the authenticated session. There are a few ways to go about doing this - please see the Authenticating section below for some examples


### Make API Calls

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

## Security

- Store credentials securely (use environment variables)
- Don't commit `rer_cookies.json` to version control
- Cookies grant full account access - treat like passwords
- Add `rer_cookies.json` to your `.gitignore`

## Limitations

- Subject to website changes breaking the wrapper
- This is an unofficial library with no support from Ofgem
