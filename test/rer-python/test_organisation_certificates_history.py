"""Tests for RER_wrapper.get_organisation_certificates_history() - GET /Organisations/{id}/Certificates/{type}/History"""
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from dotenv import load_dotenv
from rer import RER_wrapper, CertificateHistory

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

COOKIES_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'rer_cookies.json')
ORG_ID = "GEN0202802"
FROM_DATE = "05/01/2024 00:00:00 +01:00"
TO_DATE = "04/07/2026 12:14:27 +01:00"

import pytest


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
def rego_history(wrapper):
    return wrapper.get_organisation_certificates_history(ORG_ID, "REGO", from_date=FROM_DATE, to_date=TO_DATE)


@pytest.fixture(scope="module")
def roc_history(wrapper):
    return wrapper.get_organisation_certificates_history(ORG_ID, "ROC", from_date=FROM_DATE, to_date=TO_DATE)


def test_rego_returns_dict(rego_history):
    assert isinstance(rego_history, dict)


def test_rego_organisation_id(rego_history):
    assert rego_history["organisation_id"] == ORG_ID


def test_rego_cert_type(rego_history):
    assert rego_history["cert_type"] == "REGO"


def test_rego_months_is_list(rego_history):
    assert isinstance(rego_history["months"], list)


def test_rego_months_nonempty(rego_history):
    assert len(rego_history["months"]) > 0


def test_rego_each_month_has_fields(rego_history):
    for m in rego_history["months"]:
        assert isinstance(m["month"], str) and len(m["month"]) > 0
        assert isinstance(m["month_url"], str)
        assert isinstance(m["transferred_in"], int)
        assert isinstance(m["transferred_out"], int)


def test_roc_returns_dict(roc_history):
    assert isinstance(roc_history, dict)


def test_roc_cert_type(roc_history):
    assert roc_history["cert_type"] == "ROC"


def test_roc_months_is_list(roc_history):
    assert isinstance(roc_history["months"], list)


def test_print_raw_rego(rego_history):
    print(json.dumps(rego_history, indent=2))


def test_print_raw_roc(roc_history):
    print(json.dumps(roc_history, indent=2))
