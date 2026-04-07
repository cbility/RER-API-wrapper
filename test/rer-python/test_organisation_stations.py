"""Tests for RER_wrapper.get_organisation_stations() - GET /Organisations/{id}/Stations"""
import sys
import os
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from dotenv import load_dotenv
from rer import RER_wrapper

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

COOKIES_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'rer_cookies.json')

ORG_ID = "GEN0194833"


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
def stations(wrapper):
    return wrapper.get_organisation_stations(ORG_ID)


def test_returns_dict(stations):
    assert isinstance(stations, dict)


def test_organisation_id_is_correct(stations):
    assert stations["organisation_id"] == ORG_ID


def test_stations_is_list(stations):
    assert isinstance(stations["stations"], list)


def test_stations_nonempty(stations):
    assert len(stations["stations"]) > 0


def test_each_station_has_required_fields(stations):
    for s in stations["stations"]:
        assert isinstance(s["station_id"], str) and len(s["station_id"]) > 0
        assert isinstance(s["station_name"], str) and len(s["station_name"]) > 0
        assert isinstance(s["organisation_name"], str) and len(s["organisation_name"]) > 0
        assert isinstance(s["country"], str) and len(s["country"]) > 0
        assert isinstance(s["technology_group"], str) and len(s["technology_group"]) > 0
        assert isinstance(s["statuses"], list) and len(s["statuses"]) > 0
        assert isinstance(s["last_updated"], str) and len(s["last_updated"]) > 0
        assert isinstance(s["url"], str) and "/Stations/" in s["url"]


def test_station_ids_are_uuids(stations):
    import re
    uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
    for s in stations["stations"]:
        assert uuid_pattern.match(s["station_id"]), f"Not a UUID: {s['station_id']}"


def test_print_raw(stations):
    print(json.dumps(stations, indent=2))
