from unittest.mock import Mock

import pytest

from rer_client import RERClient

BREAKDOWN_HTML = """
<form>
  <table>
    <tr><th>Select</th><th>Country</th><th>Station</th><th>Technology</th><th>Output period</th><th>Count</th></tr>
    <tr>
      <td><input name="selectedCertificates" value="12345"></td>
      <td>Scotland</td><td>Wind Farm</td><td>Onshore wind</td><td>Apr 2025</td><td>106</td>
    </tr>
    <tr>
      <td><input name="selectedCertificates" value="67890"></td>
      <td>Scotland</td><td>Wind Farm</td><td>Onshore wind</td><td>May 2025</td><td>107</td>
    </tr>
    <tr>
      <td><input name="selectedCertificates" value="98765"></td>
      <td>Scotland</td><td>Wind Farm</td><td>Onshore wind</td><td>Jun 2025</td><td>108</td>
    </tr>
  </table>
  <input name="__RequestVerificationToken" value="csrf-token">
</form>
"""


def test_select_certificates_posts_all_ranges_inclusive():
    client = RERClient.__new__(RERClient)
    get_response = Mock(text=BREAKDOWN_HTML)
    post_response = Mock()
    client._request = Mock(side_effect=[get_response, post_response])

    client.select_certificates(
        "GEN0202802", "rego", "Wind Farm", "Apr 2025", "May 2025"
    )

    endpoint = "Organisations/GEN0202802/Certificates/REGO/Breakdown"
    assert client._request.call_args_list[0].args == (endpoint,)
    assert client._request.call_args_list[1].args == (endpoint,)
    assert client._request.call_args_list[1].kwargs == {
        "method": "POST",
        "data": {
            "selectedCertificates": ["12345", "67890"],
            "addSelected": "addSelected",
            "__RequestVerificationToken": "csrf-token",
        },
    }


def test_select_certificates_rejects_existing_selection():
    client = RERClient.__new__(RERClient)
    client._request = Mock(
        return_value=Mock(
            text=BREAKDOWN_HTML.replace(
                "<form>", '<form><button name="removeId" value="12345">Remove</button>'
            )
        )
    )

    with pytest.raises(ValueError, match="already selected"):  # type: ignore[call-overload]
        client.select_certificates(
            "GEN0202802", "REGO", "Wind Farm", "Apr 2025", "May 2025"
        )

    assert client._request.call_count == 1
