import json
from dataclasses import asdict
from typing import Any

from rer_api_wrapper.models import RERRequest
from rer_api_wrapper.service import RERService


def _event_to_request(event: dict[str, Any]) -> RERRequest:
    method = (
        event.get("httpMethod")
        or event.get("requestContext", {}).get("http", {}).get("method")
        or "GET"
    ).upper()
    path = (event.get("rawPath") or event.get("path") or "/").rstrip("/") or "/"

    query: dict[str, Any] = event.get("queryStringParameters") or {}
    body_data = event.get("body")
    if isinstance(body_data, dict):
        body = body_data
    elif body_data:
        try:
            body = json.loads(body_data)
        except json.JSONDecodeError:
            body = {}
    else:
        body = {}

    cookies: dict[str, str] = {}
    auth_cookies = event.get("auth_cookies")
    if isinstance(auth_cookies, dict):
        cookies = auth_cookies
    else:
        for cookie in event.get("cookies") or []:
            if "=" in cookie:
                name, value = cookie.split("=", 1)
                cookies[name] = value

        headers = event.get("headers") or {}
        cookie_header = headers.get("Cookie") or headers.get("cookie")
        if cookie_header:
            for cookie in cookie_header.split(";"):
                if "=" in cookie:
                    name, value = cookie.strip().split("=", 1)
                    cookies[name] = value

    return RERRequest(method=method, path=path, query=query, body=body, cookies=cookies)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    request = _event_to_request(event)
    service = RERService(auth_cookies=request.cookies)
    status_code, payload = service.handle_request(request)
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload, default=asdict),
    }
