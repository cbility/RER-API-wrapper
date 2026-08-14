# RER API Wrapper

Python package for wrapping the Ofgem Renewable Electricity Register (RER) portal. The RER site returns HTML, so this package handles authenticated requests, parses the relevant pages, and returns typed Python objects ready to serialize as JSON from an AWS Lambda/API Gateway wrapper.

The repository also includes a separate session-auth Lambda under `session_auth/`. That function manages RER login, MFA, cookie validation, and SmartSuite-backed cookie storage, returning cached cookies for clients to use with the main wrapper Lambda.

Deployed API usage is documented in [`docs/session-auth-api.md`](docs/session-auth-api.md).

## Installation

```bash
uv sync
```

Install from Git in another repo with:

```bash
uv add git+https://github.com/ORG/RER-API-wrapper.git
```

## Build and Deploy

The session-auth Lambda is deployed as a Docker image, so Docker, AWS CLI, and
SAM CLI must be installed and configured for the `eu-west-2` region.

Create a local `.env` file with the deployment values. It must include:

```dotenv
RER_EMAIL=...
RER_PASSWORD=...
GMAIL_TOKEN_JSON='...authorized-user-token-json...'
SMARTSUITE_API_TOKEN=...
SMARTSUITE_ACCOUNT_ID=...
SMARTSUITE_TABLE_ID=...
SMARTSUITE_RECORD_ID=...
SMARTSUITE_COOKIES_FIELD=...
```

Keep `.env` out of version control. Build the Lambda image without using a stale
dependency cache, then deploy the infrastructure and synchronize the Lambda
environment separately:

```bash
sam build --no-cached
sam deploy
./scripts/sync-session-auth-env.sh
```

Run `sam deploy` after code or infrastructure changes. Run
`./scripts/sync-session-auth-env.sh` after every deployment and whenever `.env`
values change. The sync script preserves JSON values such as `GMAIL_TOKEN_JSON`
by updating the Lambda environment through the AWS CLI structured JSON API.

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
- If cached cookies are invalid, it starts the Playwright + Gmail MFA flow asynchronously and returns `202 Accepted`; the refreshed cookies are saved to SmartSuite for a later request
- Local SAM build/deploy of the auth Lambda image requires Docker so the image can be built and pushed to ECR

## Session Auth API

Use the separate session-auth API to obtain RER cookies before calling the wrapper API.

1. Get the deployed base URL from the CloudFormation output `RERSessionAuthApiUrl`.
2. Get the API key value for `RERSessionAuthApiKey` from API Gateway.
3. Call the session-auth API root. It returns `200` with cached cookies or `202` while refreshing them.
4. Send returned cookies to the wrapper API.

Notes:
- A `202` response means refresh is running in the background; retry after a short delay.
- The wrapper API is separate and requires its own API key.

Example:

```bash
curl \
  -H "x-api-key: YOUR_SESSION_AUTH_API_KEY" \
  "https://YOUR_SESSION_AUTH_API_ID.execute-api.eu-west-2.amazonaws.com/Prod/"
```

More examples and supported routes are in [`docs/session-auth-api.md`](docs/session-auth-api.md).

## Limitations

- Subject to website changes breaking the wrapper
- This is an unofficial library with no support from Ofgem
