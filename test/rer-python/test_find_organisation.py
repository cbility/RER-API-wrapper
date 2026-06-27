"""Tests for RER_wrapper.find_organisation() - POST /Organisations/{id}/Certificates/{certType}/FindOrganisation"""
import os
import json
from dataclasses import asdict
import pytest

from rer_api_wrapper import RER_wrapper
from rer_api_wrapper.models import OrganisationSearchResult


COOKIES_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'rer_cookies.json')

# Org performing the search
SEARCHING_ORG_ID = "GEN0212976"
# Known existing organisation to find
TARGET_ORG_REFERENCE = "GEN0194833"
TARGET_ORG_NAME = "Furrowland Holdings Ltd"


@pytest.fixture(scope="module")
def wrapper():
    with open(COOKIES_FILE) as f:
        cookies = json.load(f)
    return RER_wrapper(auth_cookies=cookies)


@pytest.fixture(scope="module")
def hit(wrapper):
    return wrapper.find_organisation(SEARCHING_ORG_ID, TARGET_ORG_REFERENCE)


@pytest.fixture(scope="module")
def miss(wrapper):
    return wrapper.find_organisation(SEARCHING_ORG_ID, "GEN9999999")


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
