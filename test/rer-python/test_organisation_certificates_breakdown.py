"""Tests for RER_wrapper.get_organisation_certificates_breakdown() - GET /Organisations/{id}/Certificates/{type}/Breakdown"""
import sys
import os
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from dotenv import load_dotenv
from rer import RER_wrapper

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

COOKIES_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'rer_cookies.json')
ORG_ID = "GEN0202802"




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
def rego_breakdown(wrapper):
    return wrapper.get_organisation_certificates_breakdown(ORG_ID, "REGO")


@pytest.fixture(scope="module")
def roc_breakdown(wrapper):
    return wrapper.get_organisation_certificates_breakdown(ORG_ID, "ROC")


def test_rego_returns_dict(rego_breakdown):
    assert isinstance(rego_breakdown, dict)


def test_rego_organisation_id(rego_breakdown):
    assert rego_breakdown["organisation_id"] == ORG_ID


def test_rego_cert_type(rego_breakdown):
    assert rego_breakdown["cert_type"] == "REGO"


def test_rego_items_is_list(rego_breakdown):
    assert isinstance(rego_breakdown["items"], list)


def test_rego_items_nonempty(rego_breakdown):
    assert len(rego_breakdown["items"]) > 0


def test_rego_each_item_has_fields(rego_breakdown):
    for item in rego_breakdown["items"]:
        assert isinstance(item["action"], str)
        assert isinstance(item["country"], str)
        assert isinstance(item["station"], str)
        assert isinstance(item["technology"], str)
        assert isinstance(item["output_period"], str)
        assert isinstance(item["count"], int)


def test_roc_returns_dict(roc_breakdown):
    assert isinstance(roc_breakdown, dict)


def test_roc_cert_type(roc_breakdown):
    assert roc_breakdown["cert_type"] == "ROC"


def test_roc_items_is_list(roc_breakdown):
    assert isinstance(roc_breakdown["items"], list)


def test_print_raw_rego(rego_breakdown):
    print(json.dumps(rego_breakdown, indent=2))


def test_print_raw_roc(roc_breakdown):
    print(json.dumps(roc_breakdown, indent=2))
