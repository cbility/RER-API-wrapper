"""Tests for RER_wrapper.get_station() - GET /Organisations/Stations/{stationId}"""
import sys
import os
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from dotenv import load_dotenv
from rer import RER_wrapper

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

COOKIES_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'rer_cookies.json')

STATION_ID = "075B874C-0558-4C39-835B-69B6C84F4595"


@pytest.fixture(scope="module")
def wrapper():
    with open(COOKIES_FILE) as f:
        cookies = json.load(f)
    return RER_wrapper(
        cookies=cookies,
        user_email=os.getenv("RER_EMAIL"),
        user_password=os.getenv("RER_PASSWORD"),
    )


@pytest.fixture(scope="module")
def station(wrapper):
    return wrapper.get_station(STATION_ID)


def test_returns_dict(station):
    assert isinstance(station, dict)


def test_station_id_matches(station):
    assert station["station_id"].upper() == STATION_ID.upper()


def test_station_name_nonempty(station):
    assert isinstance(station["station_name"], str) and len(station["station_name"]) > 0


def test_organisation_name_nonempty(station):
    assert isinstance(station["organisation_name"], str) and len(station["organisation_name"]) > 0


def test_country_nonempty(station):
    assert isinstance(station["country"], str) and len(station["country"]) > 0


def test_commissioning_date_nonempty(station):
    assert isinstance(station["commissioning_date"], str) and len(station["commissioning_date"]) > 0


def test_total_installed_capacity_nonempty(station):
    assert isinstance(station["total_installed_capacity"], str) and len(station["total_installed_capacity"]) > 0


def test_technology_group_nonempty(station):
    assert isinstance(station["technology_group"], str) and len(station["technology_group"]) > 0


def test_address_nonempty(station):
    assert isinstance(station["address"], str) and len(station["address"]) > 0


def test_scheme_accreditations_is_list(station):
    assert isinstance(station["scheme_accreditations"], list)


def test_scheme_accreditations_nonempty(station):
    assert len(station["scheme_accreditations"]) > 0


def test_each_accreditation_has_required_fields(station):
    for acc in station["scheme_accreditations"]:
        assert isinstance(acc["scheme"], str) and len(acc["scheme"]) > 0
        assert isinstance(acc["accreditation_reference"], str) and len(acc["accreditation_reference"]) > 0
        assert isinstance(acc["application_date"], str) and len(acc["application_date"]) > 0
        assert isinstance(acc["effective_from"], str) and len(acc["effective_from"]) > 0
        assert isinstance(acc["status"], str) and len(acc["status"]) > 0


def test_station_capacities_is_list(station):
    assert isinstance(station["station_capacities"], list)


def test_station_capacities_nonempty(station):
    assert len(station["station_capacities"]) > 0


def test_each_capacity_has_required_fields(station):
    for cap in station["station_capacities"]:
        assert isinstance(cap["capacity_type"], str) and len(cap["capacity_type"]) > 0
        assert isinstance(cap["commissioning_date"], str) and len(cap["commissioning_date"]) > 0
        assert isinstance(cap["tic"], str) and len(cap["tic"]) > 0
        assert isinstance(cap["dnc"], str) and len(cap["dnc"]) > 0


def test_print_raw(station):
    print(json.dumps(station, indent=2))
