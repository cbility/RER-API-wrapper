"""Tests for RERClient.get_organisation_station_declarations() - GET /Organisations/{id}/StationDeclarations"""

import json
from dataclasses import asdict
import pytest
import re

from rer_client.models import StationDeclarationList

YEAR_RE = re.compile(r"^\d{4}/\d{4}$")


@pytest.fixture(scope="module")
def first_org_id(rer):
    return rer.get_user_organisations()[0].organisation_id


@pytest.fixture(scope="module")
def declarations(rer, first_org_id):
    return rer.get_organisation_station_declarations(first_org_id)


def test_returns_station_declaration_list(declarations):
    assert isinstance(declarations, StationDeclarationList)


def test_organisation_id_is_correct(declarations, first_org_id):
    assert declarations["organisation_id"] == first_org_id


def test_declarations_is_list(declarations):
    assert isinstance(declarations["declarations"], list)


def test_each_declaration_has_required_fields(declarations):
    for declaration in declarations["declarations"]:
        assert (
            isinstance(declaration["declaration_type"], str)
            and len(declaration["declaration_type"]) > 0
        )
        assert isinstance(declaration["period"], str)
        assert isinstance(declaration["status"], str)
        assert isinstance(declaration["url"], str)


def test_print_raw(declarations):
    print(json.dumps(declarations, default=asdict, indent=2))


def test_period_format(declarations):
    for declaration in declarations["declarations"]:
        if declaration["period"]:
            assert YEAR_RE.match(
                declaration["period"]
            ), f"Unexpected period format: {declaration['period']}"
