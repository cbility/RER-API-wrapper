from rer_api_wrapper.client import RER_wrapper
from rer_api_wrapper.models import (
    CertificateBreakdown,
    CertificateHistory,
    CertificatesOverview,
    OrganisationDetail,
    OrganisationSearchResult,
    OrganisationStationList,
    OrganisationSummary,
    OutputDataTaskList,
    StationDeclarationTaskList,
    StationDetail,
    User,
)


class RERService:
    def __init__(self, auth_cookies: dict[str, str]):
        self.wrapper = RER_wrapper(auth_cookies=auth_cookies)

    def get_user(self) -> User:
        return self.wrapper.get_user()

    def get_user_organisations(self) -> list[OrganisationSummary]:
        return self.wrapper.get_user_organisations()

    def get_organisation(self, organisation_id: str) -> OrganisationDetail:
        return self.wrapper.get_organisation(organisation_id)

    def get_organisation_output_data_tasks(self, organisation_id: str) -> OutputDataTaskList:
        return self.wrapper.get_organisation_output_data_tasks(organisation_id)

    def get_organisation_station_declaration_tasks(self, organisation_id: str) -> StationDeclarationTaskList:
        return self.wrapper.get_organisation_station_declaration_tasks(organisation_id)

    def get_organisation_stations(self, organisation_id: str) -> OrganisationStationList:
        return self.wrapper.get_organisation_stations(organisation_id)

    def get_station(self, station_id: str) -> StationDetail:
        return self.wrapper.get_station(station_id)

    def find_organisation(
        self,
        organisation_id: str,
        recipient_reference: str,
        cert_type: str = "REGO",
    ) -> OrganisationSearchResult | None:
        return self.wrapper.find_organisation(organisation_id, recipient_reference, cert_type)

    def get_organisation_certificates(self, organisation_id: str) -> CertificatesOverview:
        return self.wrapper.get_organisation_certificates(organisation_id)

    def get_organisation_certificates_breakdown(self, organisation_id: str, cert_type: str) -> CertificateBreakdown:
        return self.wrapper.get_organisation_certificates_breakdown(organisation_id, cert_type)

    def get_organisation_certificates_history(
        self,
        organisation_id: str,
        cert_type: str,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> CertificateHistory:
        return self.wrapper.get_organisation_certificates_history(organisation_id, cert_type, from_date, to_date)
