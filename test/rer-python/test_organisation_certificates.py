"""Tests for RER_wrapper.get_organisation_certificates() - GET /Organisations/{id}/Certificates"""
import os
import json
import pytest

from rer_api_wrapper import RER_wrapper
from rer_api_wrapper.models import CertificatesOverview, to_dict


COOKIES_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'rer_cookies.json')
ORG_ID = "GEN0202802"


def pytest_configure(config):
    pass


@pytest.fixture(scope="module")
def wrapper():
    with open(COOKIES_FILE) as f:
        cookies = json.load(f)
    return RER_wrapper(auth_cookies=cookies)


@pytest.fixture(scope="module")
def overview(wrapper):
    return wrapper.get_organisation_certificates(ORG_ID)


def test_returns_dict(overview):
    assert isinstance(overview, CertificatesOverview)


def test_organisation_id(overview):
    assert overview["organisation_id"] == ORG_ID


def test_balance_period_is_string(overview):
    assert isinstance(overview["balance_period"], str)
    assert len(overview["balance_period"]) > 0


def test_summaries_is_list(overview):
    assert isinstance(overview["summaries"], list)


def test_summaries_nonempty(overview):
    assert len(overview["summaries"]) > 0


def test_each_summary_has_fields(overview):
    for s in overview["summaries"]:
        assert s["cert_type"] in ("REGO", "ROC")
        assert isinstance(s["issued"], int)
        assert isinstance(s["breakdown_url"], str) and len(s["breakdown_url"]) > 0
        assert isinstance(s["history_url"], str) and len(s["history_url"]) > 0


def test_print_raw(overview):
    print(json.dumps(to_dict(overview), indent=2))
