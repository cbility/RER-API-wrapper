"""RER integration tests using cached HTML fixtures.

All tests use cached HTML responses from disk. To update the cache:
    uv run python test/rer-html/fetch_all_snapshots.py

Run these tests anytime, even when RER is offline:
    uv run pytest test/rer-python/test_*.py -v
"""

import pytest
import sys
from pathlib import Path

# Add test directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from cached_wrapper import CachedRERWrapper, FIXTURES_DIR


class TestWrapper:
    """Test the cached wrapper itself."""

    def test_cache_dir_exists(self):
        """Verify the cache directory exists."""
        assert FIXTURES_DIR.exists(), (
            f"Cache directory not found: {FIXTURES_DIR}. "
            f"Run 'uv run python test/rer-html/fetch_all_snapshots.py' to create fixtures."
        )

    def test_wrapper_initialization(self):
        """Test that CachedRERWrapper can be initialized."""
        wrapper = CachedRERWrapper(FIXTURES_DIR)
        assert wrapper.cache_dir == FIXTURES_DIR

    def test_wrapper_rejects_missing_cache(self):
        """Test that wrapper raises clear error when cache is missing."""
        wrapper = CachedRERWrapper(Path("/nonexistent"))

        with pytest.raises(FileNotFoundError) as exc_info:
            wrapper._request("User")

        assert "Cached response not found" in str(exc_info.value)
        assert "fetch_all_snapshots.py" in str(exc_info.value)


class TestUserEndpoints:
    """Test user-related endpoints."""

    def test_get_user(self, rer):
        """Test getting user details."""
        user = rer.get_user()
        assert user is not None

    def test_get_user_organisations(self, rer):
        """Test getting user organisations."""
        orgs = rer.get_user_organisations()
        assert isinstance(orgs, list)
        assert len(orgs) > 0, "Expected at least one organisation in cache"

        # Verify organisation structure
        org = orgs[0]
        assert hasattr(org, "organisation_id")
        assert hasattr(org, "organisation_name")


class TestOrganisationEndpoints:
    """Test organisation-related endpoints."""

    def test_get_organisation(self, rer):
        """Test getting organisation details."""
        orgs = rer.get_user_organisations()
        if not orgs:
            pytest.skip("No organisations in cache")

        org_id = orgs[0].organisation_id
        org_detail = rer.get_organisation(org_id)

        assert org_detail is not None
        assert org_detail.organisation_id == org_id

    def test_get_organisation_stations(self, rer):
        """Test getting organisation stations."""
        orgs = rer.get_user_organisations()
        if not orgs:
            pytest.skip("No organisations in cache")

        org_id = orgs[0].organisation_id
        stations = rer.get_organisation_stations(org_id)

        assert isinstance(stations, list)

    def test_get_organisation_certificates(self, rer):
        """Test getting organisation certificates."""
        orgs = rer.get_user_organisations()
        if not orgs:
            pytest.skip("No organisations in cache")

        org_id = orgs[0].organisation_id
        certs = rer.get_organisation_certificates(org_id)

        assert certs is not None


class TestStationEndpoints:
    """Test station-related endpoints."""

    def test_get_station(self, rer):
        """Test getting station details."""
        orgs = rer.get_user_organisations()
        if not orgs:
            pytest.skip("No organisations in cache")

        org_id = orgs[0].organisation_id
        stations = rer.get_organisation_stations(org_id)
        if not stations:
            pytest.skip("No stations in cache")

        station_id = stations[0].station_id
        station_detail = rer.get_station(station_id)

        assert station_detail is not None
        assert station_detail.station_id == station_id


class TestWithScraperService:
    """Test using wrapper with RERScraperService."""

    def test_service_with_wrapper(self, rer):
        """Test that RERScraperService works with the wrapper."""
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

        from rer_scraper.service import RERScraperService
        from rer_scraper.models import ScraperOperations

        # Create a mock SmartSuite client
        class MockSmartSuite:
            def get_operations(self, run_start):
                return ScraperOperations(refresh_data=True)

            def get_current_organisations(self):
                return []

            def update_organisations(self, orgs):
                pass

            def create_organisations(self, orgs):
                pass

            def map_organisation(self, org):
                return {}

        # Create a mock session auth
        class MockSessionAuth:
            def get_cookies(self):
                return {"dummy": "cookie"}

        # Create a mock retry invoker
        class MockRetryInvoker:
            def invoke(self, function_name, payload):
                pass

        # Create service with cached wrapper
        service = RERScraperService(
            smartsuite=MockSmartSuite(),
            session_auth=MockSessionAuth(),
            retry_invoker=MockRetryInvoker(),
            function_name="test-function",
            wrapper_factory=lambda cookies: rer,
        )

        # Run the service
        status_code, result = service.run(schedule_retry=False)

        assert status_code == 200
        assert result is not None
