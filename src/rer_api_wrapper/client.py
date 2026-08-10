# region imports

import logging # for logging

import requests # lighttweight web requests

from selectolax.parser import HTMLParser # for parsing HTML

import json # for saving cookies
import re # for pagination parsing
import math # for pagination calculation

from rer_api_wrapper import parsing as rer_parsing

# endregion imports

# region config

# configure logging
log = logging.getLogger(__name__)

RER_DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-GB,en;q=0.9",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    }

# endregion config

# region class

class RER_wrapper:
    """Wrapper for making authenticated requests to the RER portal.
    
    Params:
        auth_cookies: dict of cookies to use for authentication.
        headers: Optional dict of headers to use for requests. Defaults to RER_DEFAULT_HEADERS.
    """
    session: requests.Session
    base_url="https://rer.ofgem.gov.uk/"

    def __init__(self, auth_cookies: dict, headers: dict = RER_DEFAULT_HEADERS):
        self.auth_cookies = auth_cookies
        self.headers = headers

        self.authenticate(auth_cookies, headers)
    
    def get_cookies(self) -> dict:
        """Get current session cookies."""
        return self.session.cookies.get_dict()
   
    def authenticate(
            self,   
            auth_cookies: dict,
            headers: dict = RER_DEFAULT_HEADERS) -> None:
        """Authenticate with RER portal and set session.

        Creates a session with the provided cookies. 
        Throws an error if cookies are not provided.
        """

        if not auth_cookies:
            raise ValueError("Authentication cookies must be provided.")

        session = requests.Session()
        session.headers.update(headers)
        session.cookies.update(auth_cookies)
        self.session = session

        try:
            user = self.get_user()
        except requests.exceptions.ConnectionError as e:
            raise ValueError("Authentication cookies could not be validated.") from e

        log.info(f"Authenticated as {user.email} ({user.full_name}) using provided cookies.")
    

    def _request(self, endpoint: str, method: str = "GET", **kwargs) -> requests.Response:
        """Make an authenticated request to the RER portal."""
        url = self.base_url + endpoint.lstrip("/")
        response = self.session.request(method, url, **kwargs)
        if response.status_code == 200:
            return response
        elif response.status_code == 403:
            raise requests.exceptions.HTTPError(f"Request refused: {response.status_code}. This usually means the RER server is unavailable at this time.")
        else:
            log.error(f"Unexpected response when making request to {endpoint}: {response.status_code} - {response.text}")
            response.raise_for_status()
        return response

    # region getters
    def get_user(self) -> rer_parsing.User:
        """GET /User - Returns user dashboard with stats and organisation list."""
        response = self._request("User")
        return rer_parsing._parse_user(response.text)

    def get_user_organisations(
        self,
        sort_field: str | None = None,
        sort_direction: str | None = None,
    ) -> list[rer_parsing.OrganisationSummary]:
        """GET /User - Returns all organisations for the authenticated user across all pages."""
        params: dict = {"pageNumber": 1}
        if sort_field:
            params["sortField"] = sort_field
        if sort_direction:
            params["sortDirection"] = sort_direction

        response = self._request("User", params=params)
        first_html = response.text

        # Determine total pages from pagination results summary
        tree = HTMLParser(first_html)
        total_pages = 1
        results_el = tree.css_first(".moj-pagination__results")
        if results_el:
            m = re.search(r'Showing\s+(\d+)\s+to\s+(\d+)\s+of\s+(\d+)', results_el.text(strip=True))
            if m:
                start, end, total = int(m.group(1)), int(m.group(2)), int(m.group(3))
                page_size = end - start + 1
                total_pages = math.ceil(total / page_size)

        pages = [first_html]
        for page_num in range(2, total_pages + 1):
            params["pageNumber"] = page_num
            pages.append(self._request("User", params=params).text)

        return rer_parsing._parse_user_organisations(pages)

    def get_organisation(self, organisation_id: str) -> rer_parsing.OrganisationDetail:
        """GET /Organisations/OrganisationReview/{organisationId} - Returns organisation details."""
        response = self._request(f"Organisations/OrganisationReview/{organisation_id}")
        return rer_parsing._parse_organisation(response.text)

    def get_organisation_output_data_tasks(
        self,
        organisation_id: str,
        statuses: list[str] | None = None,
        sort_field: str | None = None,
        sort_direction: str | None = None,
        page_number: int = 1,
    ) -> rer_parsing.OutputDataTaskList:
        """GET /Organisations/{organisationId}/Tasks/OutputData - Returns output data tasks."""
        params: dict = {"pageNumber": page_number}
        if statuses:
            params["Statuses"] = statuses
        if sort_field:
            params["sortField"] = sort_field
        if sort_direction:
            params["sortDirection"] = sort_direction
        response = self._request(f"Organisations/{organisation_id}/Tasks/OutputData", params=params)
        return rer_parsing._parse_output_data_tasks(response.text, organisation_id)

    def get_organisation_station_declaration_tasks(
        self,
        organisation_id: str,
        sort_field: str | None = None,
        sort_direction: str | None = None,
        page_number: int = 1,
    ) -> rer_parsing.StationDeclarationTaskList:
        """GET /Organisations/{organisationId}/Tasks/StationDeclarations - Returns station declaration tasks."""
        params: dict = {"pageNumber": page_number}
        if sort_field:
            params["sortField"] = sort_field
        if sort_direction:
            params["sortDirection"] = sort_direction
        response = self._request(f"Organisations/{organisation_id}/Tasks/StationDeclarations", params=params)
        return rer_parsing._parse_station_declaration_tasks(response.text, organisation_id)

    def get_organisation_station_declarations(
        self,
        organisation_id: str,
    ) -> rer_parsing.StationDeclarationList:
        """GET /Organisations/{organisationId}/StationDeclarations - Returns station declarations."""
        response = self._request(f"Organisations/{organisation_id}/StationDeclarations")
        return rer_parsing._parse_station_declarations(response.text, organisation_id)

    def get_organisation_stations(self, organisation_id: str) -> rer_parsing.OrganisationStationList:
        """GET /Organisations/{organisationId}/Stations - Returns list of stations for the organisation."""
        response = self._request(f"Organisations/{organisation_id}/Stations")
        return rer_parsing._parse_organisation_stations(response.text, organisation_id)

    def get_station(self, station_id: str) -> rer_parsing.StationDetail:
        """GET /Organisations/Stations/{stationId} - Returns full station detail."""
        response = self._request(f"Organisations/Stations/{station_id}")
        return rer_parsing._parse_station(response.text, station_id)

    def find_organisation(
        self,
        organisation_id: str,
        recipient_reference: str,
        cert_type: str = "REGO",
    ) -> "rer_parsing.OrganisationSearchResult | None":
        """POST /Organisations/{organisationId}/Certificates/{certType}/FindOrganisation
        Searches for an organisation by reference. Returns the matched organisation or None.
        This is a read-only search — no certificates are transferred.
        """
        get_resp = self._request(f"Organisations/{organisation_id}/Certificates/{cert_type}/FindOrganisation")
        token_el = HTMLParser(get_resp.text).css_first("input[name=__RequestVerificationToken]")
        csrf = token_el.attrs.get("value", "") if token_el else ""
        post_resp = self.session.post(
            self.base_url + f"Organisations/{organisation_id}/Certificates/{cert_type}/FindOrganisation",
            data={"RecipientOrganisationReference": recipient_reference, "__RequestVerificationToken": csrf},
        )
        post_resp.raise_for_status()
        return rer_parsing._parse_find_organisation(post_resp.text)

    def get_organisation_certificates(self, organisation_id: str) -> rer_parsing.CertificatesOverview:
        """GET /Organisations/{organisationId}/Certificates - Returns certificates overview."""
        response = self._request(f"Organisations/{organisation_id}/Certificates")
        return rer_parsing._parse_certificates_overview(response.text, organisation_id)

    def get_organisation_certificates_breakdown(
        self,
        organisation_id: str,
        cert_type: str,
    ) -> rer_parsing.CertificateBreakdown:
        """GET /Organisations/{organisationId}/Certificates/{certType}/Breakdown - Returns certificate breakdown."""
        response = self._request(f"Organisations/{organisation_id}/Certificates/{cert_type}/Breakdown")
        return rer_parsing._parse_certificate_breakdown(response.text, organisation_id, cert_type)

    def get_organisation_certificates_history(
        self,
        organisation_id: str,
        cert_type: str,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> rer_parsing.CertificateHistory:
        """GET /Organisations/{organisationId}/Certificates/{certType}/History - Returns certificate transaction history."""
        params: dict = {}
        if from_date:
            params["fromDate"] = from_date
        if to_date:
            params["toDate"] = to_date
        response = self._request(
            f"Organisations/{organisation_id}/Certificates/{cert_type}/History",
            params=params,
        )
        return rer_parsing._parse_certificate_history(response.text, organisation_id, cert_type)

    # endregion getters
# endregion class

# region testing

if __name__ == "__main__":

    def _save_cookies(cookies, cookies_file="../rer_cookies.json"):
        """Save cookies to a file."""
        # remove analytics/tracking cookies
        persistent_cookies = {key: value for key, value in cookies.items() if not key.startswith("ai_")}
        with open(cookies_file, "w") as f:
            json.dump(persistent_cookies, f, indent=2)
        log.debug(f"Cookies saved to {cookies_file}")

    def _load_cookies(cookies_file="../rer_cookies.json") -> dict:
        """Load saved cookies."""
        try:
            with open(cookies_file) as f:
                return json.load(f)
        except FileNotFoundError: 
            raise FileNotFoundError(f"Cookies file not found at {cookies_file}. Please authenticate to create it.")

    logging.basicConfig(level=logging.DEBUG) # debug logging for testing

    cookies = _load_cookies()
    log.debug("Loaded cookies from file")
    rer = RER_wrapper(auth_cookies=cookies)


# endregion testing
