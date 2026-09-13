"""Tests for RERClient.get_organisation() - GET /Organisations/OrganisationReview/{id}"""

import json
from dataclasses import asdict
import pytest

from rer_client.models import OrganisationDetail


@pytest.fixture(scope="module")
def first_org_id(rer):
    # Use a known organisation ID from the fixtures
    return "GEN0213742"


@pytest.fixture(scope="module")
def organisation(rer, first_org_id):
    return rer.get_organisation_detail(first_org_id)


def test_returns_dict(organisation):
    assert isinstance(organisation, OrganisationDetail)


def test_organisation_id_matches_requested(organisation, first_org_id):
    assert organisation["organisation_id"] == first_org_id


def test_organisation_id_format(organisation):
    assert organisation["organisation_id"].startswith("GEN")
    assert len(organisation["organisation_id"]) == 10


def test_name_is_nonempty_string(organisation):
    assert isinstance(organisation["name"], str)
    assert len(organisation["name"]) > 0


def test_type_is_nonempty_string(organisation):
    assert isinstance(organisation["type"], str)
    assert len(organisation["type"]) > 0


def test_status_is_nonempty_string(organisation):
    assert isinstance(organisation["status"], str)
    assert len(organisation["status"]) > 0


def test_address_is_nonempty_string(organisation):
    assert isinstance(organisation["address"], str)
    assert len(organisation["address"]) > 0
    # Should contain street, city, postcode, and country
    assert " " in organisation["address"]


def test_contact_has_required_fields(organisation):
    contact = organisation["contact"]
    assert isinstance(contact["name"], str) and len(contact["name"]) > 0
    assert isinstance(contact["email"], str) and "@" in contact["email"]


def test_print_raw(organisation):
    print(json.dumps(organisation, default=asdict, indent=2))
