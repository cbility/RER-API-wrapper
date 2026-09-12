"""Full integration tests for the RER API Lambda handler using cached HTML.

These tests run the ACTUAL Lambda handler code with NO mocking of the handler logic.
The only difference from production is that HTTP requests are intercepted and served
from cached HTML files instead of making live requests to the RER portal.

This is a true end-to-end integration test:
- ✅ Real Lambda handler function
- ✅ Real RERService class
- ✅ Real RERClient class
- ✅ Cached HTML responses (no live RER requests)
- ✅ No SmartSuite writes (dry_run mode)

Usage:
    # Run all Lambda handler integration tests
    uv run pytest test/rer-python/test_lambda_handler.py -v

    # Run specific test
    uv run pytest test/rer-python/test_lambda_handler.py::test_handler_user_endpoint -v

Requirements:
    - Cached HTML files in test/rer-html/snapshots/latest/
    - Run 'uv run python test/rer-html/fetch_all_snapshots.py' to update cache
    - Valid RER cookies in rer_cookies.json (for authentication)
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch
import requests

from rer_api_wrapper.lambda_handler import handler
from cached_wrapper import CachedRERWrapper, FIXTURES_DIR


@pytest.fixture(scope="module")
def cached_wrapper():
    """Create a cached wrapper to serve HTML from disk."""
    return CachedRERWrapper(FIXTURES_DIR)


@pytest.fixture(scope="module")
def mock_cookies():
    """Return mock cookies - just needs to be non-empty for auth."""
    return {"session": "test-session-cookie"}


@pytest.fixture(scope="module")
def mock_context():
    """Create a mock Lambda context."""
    from unittest.mock import Mock

    context = Mock()
    context.function_name = "rer-api-handler"
    context.memory_limit_in_mb = 128
    context.invoked_function_arn = (
        "arn:aws:lambda:eu-west-2:123456789012:function:rer-api"
    )
    context.aws_request_id = "test-request-id"
    return context


def make_event(
    path: str,
    method: str = "GET",
    query: dict | None = None,
    body: dict | None = None,
    cookies: dict | None = None,
):
    """Helper to create test events."""
    if cookies is None:
        cookies = {"session": "test-cookie"}

    event = {
        "httpMethod": method,
        "path": path,
        "queryStringParameters": query or {},
        "auth_cookies": cookies,
    }
    if body:
        event["body"] = json.dumps(body)
    return event


def intercept_requests_with_cache(cached_wrapper):
    """Context manager to intercept requests and serve cached HTML."""
    from unittest.mock import Mock
    import requests

    def mock_request(self, method, url, **kwargs):
        """Intercept HTTP requests and return cached responses."""
        # Extract endpoint from URL
        # URL format: https://rer.ofgem.gov.uk/User or https://rer.ofgem.gov.uk/Organisations/GEN123/Stations
        path = url.replace("https://rer.ofgem.gov.uk/", "")

        # Get params from kwargs
        params = kwargs.get("params", {})

        try:
            # Use cached wrapper to get response
            response = cached_wrapper._request(path, method, params=params)
            return response
        except FileNotFoundError as e:
            # Create error response
            error_response = Mock()
            error_response.status_code = 404
            error_response.text = f"Cache not found: {e}"
            error_response.content = error_response.text.encode()
            return error_response

    return mock_request


class TestLambdaHandlerFullIntegration:
    """Full integration tests - real handler, real service, cached HTML."""

    @pytest.fixture(autouse=True)
    def use_cached_html(self, cached_wrapper):
        """Intercept all HTTP requests and serve from cache."""
        # Patch the requests.Session methods to use cached HTML
        mock_request = intercept_requests_with_cache(cached_wrapper)

        with patch.object(requests.Session, "request", mock_request):
            with patch.object(
                requests.Session,
                "get",
                lambda self, url, **kwargs: mock_request(self, "GET", url, **kwargs),
            ):
                with patch.object(
                    requests.Session,
                    "post",
                    lambda self, url, **kwargs: mock_request(
                        self, "POST", url, **kwargs
                    ),
                ):
                    yield

    def test_handler_user_endpoint(self, mock_context, mock_cookies):
        """Test the /user endpoint - full integration with cached HTML."""
        event = make_event("/user", cookies=mock_cookies)

        # This runs the REAL handler function
        response = handler(event, mock_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "email" in body
        assert "full_name" in body

    def test_handler_user_organisations_endpoint(self, mock_context, mock_cookies):
        """Test /user/organisations endpoint - full integration."""
        event = make_event("/user/organisations", cookies=mock_cookies)
        response = handler(event, mock_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert isinstance(body, list)
        assert len(body) > 0

    def test_handler_organisation_endpoint(self, mock_context, mock_cookies):
        """Test /organisations/{id} endpoint - full integration."""
        event = make_event("/organisations/GEN0212970", cookies=mock_cookies)
        response = handler(event, mock_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["organisation_id"] == "GEN0212970"

    def test_handler_stations_endpoint(self, mock_context, mock_cookies):
        """Test /organisations/{id}/stations endpoint - full integration."""
        event = make_event("/organisations/GEN0212970/stations", cookies=mock_cookies)
        response = handler(event, mock_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert isinstance(body, list)

    def test_handler_certificates_endpoint(self, mock_context, mock_cookies):
        """Test /organisations/{id}/certificates endpoint - full integration."""
        event = make_event(
            "/organisations/GEN0212970/certificates", cookies=mock_cookies
        )
        response = handler(event, mock_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "organisation_id" in body

    def test_handler_404_for_unknown_endpoint(self, mock_context, mock_cookies):
        """Test that unknown endpoints return 404 - full integration."""
        event = make_event("/unknown/endpoint", cookies=mock_cookies)
        response = handler(event, mock_context)

        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert "error" in body
