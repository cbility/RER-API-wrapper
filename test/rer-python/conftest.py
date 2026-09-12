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


@pytest.fixture(scope="module")
def rer():
    """RER wrapper that serves cached HTML responses from disk.

    Uses cached HTML snapshots from test/rer-html/snapshots/latest/.
    Fails with FileNotFoundError if a cached response is not found.

    To update cache fixtures:
        uv run python test/rer-html/fetch_all_snapshots.py
    """
    return CachedRERWrapper(cache_dir=FIXTURES_DIR)
