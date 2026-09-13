"""Shared setup for RER integration tests using cached HTML fixtures.

All tests use cached HTML responses from disk. To update the cache, run:
    uv run python test/rer-html/fetch_all_snapshots.py
"""

import sys
from pathlib import Path

import pytest

# Add test directory to path for cached_wrapper import
sys.path.insert(0, str(Path(__file__).parent))
from cached_wrapper import CachedRERWrapper, FIXTURES_DIR


def pytest_addoption(parser):
    """Add custom command-line options for tests."""
    parser.addoption(
        "--dry-run",
        action="store_true",
        default=True,
        help="Enable dry_run mode (default: True, no SmartSuite writes)",
    )
    parser.addoption(
        "--no-dry-run",
        action="store_false",
        dest="dry_run",
        help="Disable dry_run mode (real SmartSuite writes)",
    )


@pytest.fixture(scope="session")
def dry_run_mode(request):
    """Get dry_run setting from command line."""
    return request.config.getoption("--dry-run")


@pytest.fixture(scope="module")
def rer():
    """RER wrapper that serves cached HTML responses from disk.

    Uses cached HTML snapshots from test/rer-html/snapshots/latest/.
    Fails with FileNotFoundError if a cached response is not found.

    To update cache fixtures:
        uv run python test/rer-html/fetch_all_snapshots.py
    """
    return CachedRERWrapper(cache_dir=FIXTURES_DIR)
