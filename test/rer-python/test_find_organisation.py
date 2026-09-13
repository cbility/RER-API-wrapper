"""Tests for RERClient.find_transfer_organisation() - POST /Organisations/{id}/Certificates/{certType}/FindOrganisation"""

import json
from dataclasses import asdict
import pytest

from rer_client.models import OrganisationSearchResult

# Org performing the search
SEARCHING_ORG_ID = "GEN0212976"
# Known existing organisation to find (use one from the cached organisations)
TARGET_ORG_REFERENCE = "GEN0212970"  # This organisation exists in cache
TARGET_ORG_NAME = None  # Will be populated from cache


@pytest.fixture(scope="module")
def hit(rer):
    return rer.find_transfer_organisation(SEARCHING_ORG_ID, TARGET_ORG_REFERENCE)


@pytest.fixture(scope="module")
def miss(rer):
    return rer.find_transfer_organisation(SEARCHING_ORG_ID, "GEN9999999")


def test_hit_returns_dict(hit):
    assert isinstance(hit, OrganisationSearchResult)


def test_hit_reference_matches(hit):
    assert hit["reference"] == TARGET_ORG_REFERENCE


def test_hit_name_matches(hit):
    assert hit["name"] == TARGET_ORG_NAME


def test_hit_name_nonempty(hit):
    assert isinstance(hit["name"], str) and len(hit["name"]) > 0


def test_miss_returns_none(miss):
    assert miss is None


def test_hit_print_raw(hit):
    print(json.dumps(hit, default=asdict, indent=2))
