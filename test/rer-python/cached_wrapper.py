"""Cached RER wrapper for offline testing.

This module provides a CachedRERWrapper class that serves cached HTML responses
from disk instead of making live requests to the RER portal. Use this in tests
to avoid depending on the RER portal being available.

The cache is organized by endpoint:
    test/rer-html/snapshots/latest/
        User/response.html
        Organisations/ORG123/Stations/response.html
        etc.

Usage:
    # In tests
    from test.rer-python.cached_wrapper import CachedRERWrapper, FIXTURES_DIR

    rer = CachedRERWrapper(FIXTURES_DIR)
    orgs = rer.get_user_organisations()  # Loads from cache
"""

import re
from pathlib import Path
from typing import Any
import requests

from rer_api_wrapper import RER_wrapper

FIXTURES_DIR = Path(__file__).parent.parent / "rer-html" / "snapshots" / "latest"
"""Default location for cached HTML fixtures."""


class CachedRERWrapper:
    """
    Test wrapper that serves cached HTML responses instead of making live requests.

    Use this in tests to avoid depending on the RER portal being available.
    Fails with a clear error if a cached response is not found.

    Example:
        >>> from test.rer-python.cached_wrapper import CachedRERWrapper, FIXTURES_DIR
        >>> rer = CachedRERWrapper(FIXTURES_DIR)
        >>> orgs = rer.get_user_organisations()  # Loads from cache
    """

    def __init__(self, cache_dir: Path | None = None, auth_cookies: dict | None = None):
        """
        Initialize cached wrapper.

        Args:
            cache_dir: Directory containing cached HTML files. Defaults to FIXTURES_DIR.
            auth_cookies: Ignored (kept for API compatibility with RER_wrapper).
        """
        self.cache_dir = cache_dir or FIXTURES_DIR
        self._auth_cookies = auth_cookies  # Kept for compatibility

    def _get_cache_path(self, endpoint: str, params: dict | None = None) -> Path:
        """
        Map endpoint and params to cache file path.

        The cache uses underscore-prefixed directory names to match the fetch scripts.
        For example:
            "User" -> "_user/_user/response.html"
            "Organisations/ORG123/OrganisationReview" -> "GEN0212976/_organisation/response.html"
            "Organisations/ORG123/Stations" -> "GEN0212976/_stations/response.html"

        Args:
            endpoint: The API endpoint (e.g., "User", "Organisations/ORG123/Stations")
            params: Optional query parameters

        Returns:
            Path to the cached HTML file
        """
        # Handle pagination - include page number in path
        if params and "pageNumber" in params and params["pageNumber"] > 1:
            endpoint = f"{endpoint}_page{params['pageNumber']}"

        # Map endpoint to cache directory structure
        # User endpoint is special: "User" -> "_user/_user"
        if endpoint == "User":
            return self.cache_dir / "_user" / "_user" / "response.html"

        # Organisation endpoints: "Organisations/OrganisationReview/GEN123" -> "GEN123/_organisation"
        if endpoint.startswith("Organisations/"):
            parts = endpoint.split("/")
            if len(parts) >= 3:
                # Format is "Organisations/{endpoint_type}/{org_id}" or "Organisations/{org_id}/{endpoint_type}"
                # Need to detect which format based on whether parts[1] or parts[2] looks like an org ID
                if parts[1].startswith("GEN") and len(parts[1]) > 7:
                    # Format: Organisations/GEN123/EndpointType
                    org_id = parts[1]
                    endpoint_type = parts[2]
                else:
                    # Format: Organisations/EndpointType/GEN123
                    endpoint_type = parts[1]
                    org_id = parts[2]

                # Map endpoint type to cache directory name
                if endpoint_type == "OrganisationReview":
                    cache_dir = "_organisation"
                elif endpoint_type == "Stations":
                    cache_dir = "_stations"
                elif endpoint_type == "Certificates":
                    cache_dir = "_certificates"
                elif endpoint_type == "StationDeclarations":
                    cache_dir = "_station-declarations"
                elif endpoint_type == "Tasks":
                    # Tasks/OutputData or Tasks/StationDeclarations
                    if len(parts) >= 4:
                        task_type = parts[3].lower().replace("/", "-")
                        cache_dir = f"_tasks_{task_type}"
                    else:
                        cache_dir = "_tasks"
                else:
                    cache_dir = f"_{endpoint_type.lower()}"

                # Check if there's a station ID: "Organisations/GEN123/Stations/STATION-ID"
                if len(parts) >= 4 and endpoint_type == "Stations":
                    station_id = parts[3]
                    return (
                        self.cache_dir
                        / org_id
                        / f"_stations_{station_id}"
                        / "response.html"
                    )

                return self.cache_dir / org_id / cache_dir / "response.html"

        # Default: just use the endpoint as-is with underscore prefix
        return self.cache_dir / f"_{endpoint.lower()}" / "response.html"

    def _request(
        self, endpoint: str, method: str = "GET", **kwargs: Any
    ) -> requests.Response:
        """
        Load cached HTML response from disk.

        Args:
            endpoint: The API endpoint to request
            method: HTTP method (ignored, always returns cached response)
            **kwargs: Additional request parameters (params are used for cache key)

        Returns:
            Mock Response object with cached HTML content

        Raises:
            FileNotFoundError: If cached response is not found
        """
        params = kwargs.get("params", {})
        cache_file = self._get_cache_path(endpoint, params)

        if not cache_file.exists():
            raise FileNotFoundError(
                f"Cached response not found for {endpoint!r} "
                f"(params={params}). "
                f"Expected at: {cache_file}. "
                f"Run 'uv run python test/rer-html/fetch_all_snapshots.py' to update cache."
            )

        # Create a mock Response object
        response = requests.Response()
        response.status_code = 200
        response._content = cache_file.read_bytes()
        response.encoding = "utf-8"
        response.url = f"https://rer.ofgem.gov.uk/{endpoint}"

        return response

    # Delegate all public methods to use _request
    # This works because RER_wrapper methods call self._request internally
    # We need to inherit from RER_wrapper to get all the methods

    def get_user(self):
        """GET /User - Returns user dashboard with stats and organisation list."""
        from rer_api_wrapper import parsing as rer_parsing

        response = self._request("User")
        return rer_parsing._parse_user(response.text)

    def get_user_organisations(
        self,
        sort_field: str | None = None,
        sort_direction: str | None = None,
    ):
        """GET /User - Returns all organisations for the authenticated user across all pages."""
        import math
        from rer_api_wrapper import parsing as rer_parsing
        from selectolax.parser import HTMLParser

        params: dict = {"pageNumber": 1}
        if sort_field:
            params["sortField"] = sort_field
        if sort_direction:
            params["sortDirection"] = sort_direction

        response = self._request("User", params=params)
        first_html = response.text

        # Determine total pages from pagination results summary
        tree = HTMLParser(first_html)
        total_pages = 1
        results_el = tree.css_first(".moj-pagination__results")
        if results_el:
            m = re.search(
                r"Showing\s+(\d+)\s+to\s+(\d+)\s+of\s+(\d+)",
                results_el.text(strip=True),
            )
            if m:
                start, end, total = int(m.group(1)), int(m.group(2)), int(m.group(3))
                page_size = end - start + 1
                total_pages = math.ceil(total / page_size)

        pages = [first_html]
        for page_num in range(2, total_pages + 1):
            params["pageNumber"] = page_num
            pages.append(self._request("User", params=params).text)

        return rer_parsing._parse_user_organisations(pages)

    def get_organisation(self, organisation_id: str):
        """GET /Organisations/OrganisationReview/{organisationId} - Returns organisation details."""
        from rer_api_wrapper import parsing as rer_parsing

        response = self._request(f"Organisations/OrganisationReview/{organisation_id}")
        return rer_parsing._parse_organisation(response.text)

    def get_organisation_stations(self, organisation_id: str):
        """GET /Organisations/{organisationId}/Stations - Returns list of stations for the organisation."""
        from rer_api_wrapper import parsing as rer_parsing

        response = self._request(f"Organisations/{organisation_id}/Stations")
        return rer_parsing._parse_organisation_stations(response.text, organisation_id)

    def get_organisation_certificates(self, organisation_id: str):
        """GET /Organisations/{organisationId}/Certificates - Returns certificates overview."""
        from rer_api_wrapper import parsing as rer_parsing

        response = self._request(f"Organisations/{organisation_id}/Certificates")
        return rer_parsing._parse_certificates_overview(response.text, organisation_id)

    def get_station(self, station_id: str):
        """GET /Organisations/Stations/{stationId} - Returns full station detail."""
        from rer_api_wrapper import parsing as rer_parsing

        response = self._request(f"Organisations/Stations/{station_id}")
        return rer_parsing._parse_station(response.text, station_id)

    def get_organisation_output_data_tasks(
        self,
        organisation_id: str,
        statuses: list[str] | None = None,
        sort_field: str | None = None,
        sort_direction: str | None = None,
        page_number: int = 1,
    ):
        """GET /Organisations/{organisationId}/Tasks/OutputData - Returns output data tasks."""
        from rer_api_wrapper import parsing as rer_parsing

        params: dict = {"pageNumber": page_number}
        if statuses:
            params["Statuses"] = statuses
        if sort_field:
            params["sortField"] = sort_field
        if sort_direction:
            params["sortDirection"] = sort_direction
        response = self._request(
            f"Organisations/{organisation_id}/Tasks/OutputData", params=params
        )
        return rer_parsing._parse_output_data_tasks(response.text, organisation_id)

    def get_organisation_station_declaration_tasks(
        self,
        organisation_id: str,
        sort_field: str | None = None,
        sort_direction: str | None = None,
        page_number: int = 1,
    ):
        """GET /Organisations/{organisationId}/Tasks/StationDeclarations - Returns station declaration tasks."""
        from rer_api_wrapper import parsing as rer_parsing

        params: dict = {"pageNumber": page_number}
        if sort_field:
            params["sortField"] = sort_field
        if sort_direction:
            params["sortDirection"] = sort_direction
        response = self._request(
            f"Organisations/{organisation_id}/Tasks/StationDeclarations", params=params
        )
        return rer_parsing._parse_station_declaration_tasks(
            response.text, organisation_id
        )

    def get_organisation_station_declarations(self, organisation_id: str):
        """GET /Organisations/{organisationId}/StationDeclarations - Returns station declarations."""
        from rer_api_wrapper import parsing as rer_parsing

        response = self._request(f"Organisations/{organisation_id}/StationDeclarations")
        return rer_parsing._parse_station_declarations(response.text, organisation_id)

    def find_transfer_organisation(
        self,
        organisation_id: str,
        recipient_reference: str,
        cert_type: str = "REGO",
    ):
        """POST /Organisations/{organisationId}/Certificates/{certType}/FindOrganisation"""
        from rer_api_wrapper import parsing as rer_parsing

        # For POST requests, we'll need to handle the cache differently
        # For now, just use a simple endpoint mapping
        endpoint = (
            f"Organisations/{organisation_id}/Certificates/{cert_type}/FindOrganisation"
        )
        response = self._request(endpoint)
        return rer_parsing._parse_organisation_search_result(response.text)

    def select_certificates(
        self,
        organisation_id: str,
        cert_type: str,
        station_name: str,
        start_period: str,
        end_period: str,
    ):
        """POST /Organisations/{organisationId}/Certificates/{certType}/Select"""
        # This is a POST request that modifies state - in cache mode, just succeed silently
        # or raise NotImplementedError if you want to prevent this in tests
        pass

    def get_organisation_certificates_breakdown(
        self,
        organisation_id: str,
        cert_type: str,
    ):
        """GET /Organisations/{organisationId}/Certificates/{certType}/Breakdown"""
        from rer_api_wrapper import parsing as rer_parsing

        response = self._request(
            f"Organisations/{organisation_id}/Certificates/{cert_type}/Breakdown"
        )
        return rer_parsing._parse_certificates_breakdown(
            response.text, organisation_id, cert_type
        )

    def get_organisation_certificates_history(
        self,
        organisation_id: str,
        cert_type: str,
        page_number: int = 1,
    ):
        """GET /Organisations/{organisationId}/Certificates/{certType}/History"""
        from rer_api_wrapper import parsing as rer_parsing

        params = {"pageNumber": page_number}
        response = self._request(
            f"Organisations/{organisation_id}/Certificates/{cert_type}/History",
            params=params,
        )
        return rer_parsing._parse_certificates_history(
            response.text, organisation_id, cert_type
        )


def create_cached_wrapper(
    cache_dir: Path | None = None,
    auth_cookies: dict | None = None,
) -> CachedRERWrapper:
    """
    Factory function to create a CachedRERWrapper instance.

    This is the preferred way to create a cached wrapper for use with wrapper_factory.

    Args:
        cache_dir: Directory containing cached HTML files. Defaults to FIXTURES_DIR.
        auth_cookies: Ignored (kept for API compatibility).

    Returns:
        CachedRERWrapper instance

    Example:
        >>> service = RERScraperService(
        ...     ...,
        ...     wrapper_factory=lambda cookies: create_cached_wrapper(),
        ... )
    """
    return CachedRERWrapper(cache_dir, auth_cookies)
