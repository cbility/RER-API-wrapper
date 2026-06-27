# RER API Wrapper

Python package for wrapping the Ofgem Renewable Electricity Register (RER) portal. The RER site returns HTML, so this package handles authenticated requests, parses the relevant pages, and returns typed Python objects ready to serialize as JSON from an AWS Lambda/API Gateway wrapper.

## Installation

```bash
uv sync
```

Install from Git in another repo with:

```bash
uv add git+https://github.com/ORG/RER-API-wrapper.git
```

## Getting started

To use the package you need authenticated RER cookies. The helper script at `test/bootstrap_rer_cookies.py` can regenerate local cookies for development.


### Make API Calls

```python
import json

from rer_api_wrapper import RERService
from rer_api_wrapper.models import to_dict

cookies = {"cookie-name": "cookie-value"}
service = RERService(auth_cookies=cookies)

user = service.get_user()
print(json.dumps(to_dict(user), indent=2))
```

## Wrapped Endpoints

- `GET /User` - User dashboard
- `GET /User/Activity` - User activity log
- `GET /Organisations/{id}` - Organisation details
- `GET /Organisations/{id}/Tasks/OutputData` - Output data tasks

## Example: Get Organisation Tasks

```python
from rer_api_wrapper import RERService

cookies = {"cookie-name": "cookie-value"}
service = RERService(auth_cookies=cookies)

org_id = "GEN0215941"
tasks = service.get_organisation_output_data_tasks(org_id)
```

## Security

- Store credentials securely (use environment variables)
- Don't commit `rer_cookies.json` to version control
- Cookies grant full account access - treat like passwords
- Add `rer_cookies.json` to your `.gitignore`

## Limitations

- Subject to website changes breaking the wrapper
- This is an unofficial library with no support from Ofgem
