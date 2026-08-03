# Session Auth API

This API is the client-facing entry point for making authenticated RER wrapper requests without managing RER session cookies in the client.

## What It Does

For each incoming request, the session-auth Lambda:

1. checks SmartSuite for cached RER cookies
2. validates those cookies against the RER portal
3. if needed, performs the RER login flow including MFA
4. stores refreshed cookies back in SmartSuite
5. invokes the main wrapper Lambda with the cookies attached
6. returns the wrapper Lambda response to the client

The client only talks to the session-auth API.

## Base URL

Use the CloudFormation stack output named `RERSessionAuthApiUrl`.

Example shape:

```text
https://YOUR_API_ID.execute-api.eu-west-2.amazonaws.com/Prod/
```

Important:
- The deployed route is `/{proxy+}`.
- Do not call the bare root URL by itself.
- Call a concrete path such as `/user` or `/organisations/GEN0215941`.

## Authentication

Send the API Gateway API key in the `x-api-key` header.

Example:

```http
x-api-key: YOUR_SESSION_AUTH_API_KEY
```

This is the separate API key for the session-auth API, not the wrapper API key.

## Request Format

Send the same path, method, query string, and JSON body that you would send to the main wrapper API.

Do not send RER cookies from the client. The session-auth Lambda injects them internally.

## Supported Routes

These are the wrapper routes currently supported through the session-auth API:

- `GET /user`
- `GET /user/organisations`
- `GET /organisations/{organisation_id}`
- `GET /organisations/{organisation_id}/tasks/output-data`
- `GET /organisations/{organisation_id}/tasks/station-declarations`
- `GET /organisations/{organisation_id}/stations`
- `GET /organisations/{organisation_id}/certificates`
- `GET /organisations/{organisation_id}/certificates/{cert_type}/breakdown`
- `GET /organisations/{organisation_id}/certificates/{cert_type}/history`
- `GET /stations/{station_id}`
- `POST /organisations/{organisation_id}/certificates/{cert_type}/find-organisation`

Use lowercase wrapper paths as shown above.

## Examples

### Get the current user

```bash
curl \
  -H "x-api-key: YOUR_SESSION_AUTH_API_KEY" \
  "https://YOUR_API_ID.execute-api.eu-west-2.amazonaws.com/Prod/user"
```

### Get user organisations

```bash
curl \
  -H "x-api-key: YOUR_SESSION_AUTH_API_KEY" \
  "https://YOUR_API_ID.execute-api.eu-west-2.amazonaws.com/Prod/user/organisations?sortField=name&sortDirection=Ascending"
```

### Get an organisation

```bash
curl \
  -H "x-api-key: YOUR_SESSION_AUTH_API_KEY" \
  "https://YOUR_API_ID.execute-api.eu-west-2.amazonaws.com/Prod/organisations/GEN0215941"
```

### Get output data tasks

```bash
curl \
  -H "x-api-key: YOUR_SESSION_AUTH_API_KEY" \
  "https://YOUR_API_ID.execute-api.eu-west-2.amazonaws.com/Prod/organisations/GEN0215941/tasks/output-data?pageNumber=1"
```

### Find an organisation for certificate transfer lookup

```bash
curl \
  -X POST \
  -H "x-api-key: YOUR_SESSION_AUTH_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"recipient_reference":"ORG123456"}' \
  "https://YOUR_API_ID.execute-api.eu-west-2.amazonaws.com/Prod/organisations/GEN0215941/certificates/REGO/find-organisation"
```

You can also pass `recipientReference` as a query parameter, but JSON body input is preferred.

## Response Behavior

- Successful responses are returned directly from the wrapper Lambda.
- Response bodies are JSON.
- Unsupported routes return `404` with `{"error": "route not found"}`.
- `find-organisation` without a recipient reference returns `400`.

## Operational Notes

- If valid cookies are already cached in SmartSuite, requests should complete relatively quickly.
- If cookies are missing or expired, the request may take significantly longer because the Lambda must complete the RER login and MFA flow before forwarding the request.
- SmartSuite stores the cookie payload for reuse across requests.

## Required Lambda Configuration

The deployed session-auth Lambda expects these environment variables to be configured:

- `RER_EMAIL`
- `RER_PASSWORD`
- `GMAIL_TOKEN_JSON`
- `SMARTSUITE_API_TOKEN`
- `SMARTSUITE_ACCOUNT_ID`
- `SMARTSUITE_TABLE_ID`
- `SMARTSUITE_RECORD_ID`
- `SMARTSUITE_COOKIES_FIELD`

Optional:

- `SMARTSUITE_REFRESHED_AT_FIELD`
- `SMARTSUITE_API_URL`
- `SMARTSUITE_TIMEOUT_SECONDS`
- `RER_MFA_MAX_RETRIES`
- `RER_MFA_WAIT_SECONDS`
- `PLAYWRIGHT_HEADLESS`

## Troubleshooting

- `403` or API Gateway auth failure: check the `x-api-key` value.
- `404 route not found`: check that you are calling a supported lowercase wrapper route.
- Long-running request: likely cookie refresh or MFA flow.
- Lambda failure during refresh: check SmartSuite config, Gmail token, Playwright runtime, and RER credentials.
