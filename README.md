# RER API Wrapper

Python package for wrapping the Ofgem Renewable Electricity Register (RER) portal. The RER site returns HTML, so this package handles authenticated requests, parses the relevant pages, and returns typed Python objects ready to serialize as JSON from an AWS Lambda/API Gateway wrapper.

The repository also includes a separate session-auth Lambda under `session_auth/`. That function manages RER login, MFA, cookie validation, SmartSuite-backed cookie storage, and then invokes the main wrapper Lambda with refreshed session cookies attached.

Deployed API usage is documented in [`docs/session-auth-api.md`](docs/session-auth-api.md).

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
- Send an `x-api-key` header when calling the deployed wrapper API
- Send an `x-api-key` header when calling the separate session-auth API
- Don't commit `rer_cookies.json` to version control
- Cookies grant full account access - treat like passwords
- Add `rer_cookies.json` to your `.gitignore`

## Session Auth Lambda

- Source lives in `session_auth/`
- It is deployed as a separate API Gateway endpoint and Lambda function
- `RERSessionAuthFunction` is packaged as a Lambda container image so Playwright/Chromium is available at runtime
- It loads cached cookies from a SmartSuite record using `Authorization: Token ...` plus the `ACCOUNT-ID` workspace header
- Configure `SMARTSUITE_ACCOUNT_ID`, `SMARTSUITE_TABLE_ID`, `SMARTSUITE_RECORD_ID`, and `SMARTSUITE_COOKIES_FIELD` in the auth Lambda environment
- If cached cookies are invalid, it uses the legacy Playwright + Gmail MFA flow to obtain fresh cookies, saves them, and invokes the main wrapper Lambda
- Local SAM build/deploy of the auth Lambda image requires Docker so the image can be built and pushed to ECR

## Session Auth API

Use the separate session-auth API when your client should not manage RER cookies directly.

1. Get the deployed base URL from the CloudFormation output `RERSessionAuthApiUrl`.
2. Get the API key value for `RERSessionAuthApiKey` from API Gateway.
3. Call a concrete wrapper route under that base URL, such as `/user` or `/organisations/{id}`.

Notes:
- The API Gateway route is `/{proxy+}`, so the bare stage root is not a valid endpoint.
- Routes are the wrapper routes, not the upstream RER portal URLs.
- You do not need to send RER cookies from the client.
- The auth Lambda checks cached cookies in SmartSuite, refreshes them if needed, then forwards the request to the main wrapper Lambda.
- A request that triggers RER login + MFA will take longer than a request that can reuse cached cookies.

Example:

```bash
curl \
  -H "x-api-key: YOUR_SESSION_AUTH_API_KEY" \
  "https://YOUR_SESSION_AUTH_API_ID.execute-api.eu-west-2.amazonaws.com/Prod/user"
```

More examples and supported routes are in [`docs/session-auth-api.md`](docs/session-auth-api.md).

## Limitations

- Subject to website changes breaking the wrapper
- This is an unofficial library with no support from Ofgem
