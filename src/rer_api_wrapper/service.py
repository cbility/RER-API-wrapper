from __future__ import annotations

from typing import Any

from rer_api_wrapper.client import RER_wrapper
from rer_api_wrapper.models import (
    CertificateBreakdown,
    CertificateHistory,
    CertificatesOverview,
    RERRequest,
    OrganisationDetail,
    OrganisationSearchResult,
    OrganisationStation,
    OrganisationSummary,
    OutputDataTaskList,
    StationDeclarationList,
    StationDeclarationTaskList,
    StationDetail,
    User,
)


class RERService:
    def __init__(self, auth_cookies: dict[str, str]):
        self.wrapper = RER_wrapper(auth_cookies=auth_cookies)

    def handle_request(self, request: RERRequest) -> tuple[int, Any]:
        method = request.method.upper()
        path = request.path.rstrip("/") or "/"
        parts = path.strip("/").split("/") if path != "/" else []
        parts_lower = [part.lower() for part in parts]
        query = request.query
        body = request.body

        if method == "GET" and path == "/user":
            return 200, self.get_user()

        if method == "GET" and path == "/user/organisations":
            return 200, self.get_user_organisations(
                    sort_field=query.get("sortField"),
                    sort_direction=query.get("sortDirection"),
                )

        if method == "GET" and len(parts) >= 2 and parts_lower[:1] == ["organisations"]:
            organisation_id = parts[1]

            if len(parts) == 2:
                return 200, self.get_organisation(organisation_id)

            if len(parts) == 4 and parts_lower[2:4] == ["tasks", "output-data"]:
                statuses = query.get("Statuses") or query.get("statuses")
                if isinstance(statuses, str):
                    statuses = [value for value in statuses.split(",") if value]
                return 200, self.get_organisation_output_data_tasks(
                    organisation_id,
                    statuses=statuses,
                    sort_field=query.get("sortField"),
                    sort_direction=query.get("sortDirection"),
                    page_number=int(query.get("pageNumber", 1)),
                )

            if len(parts) == 4 and parts_lower[2:4] == ["tasks", "station-declarations"]:
                return 200, self.get_organisation_station_declaration_tasks(
                    organisation_id,
                    sort_field=query.get("sortField"),
                    sort_direction=query.get("sortDirection"),
                    page_number=int(query.get("pageNumber", 1)),
                )

            if len(parts) == 3 and parts_lower[2] == "station-declarations":
                return 200, self.get_organisation_station_declarations(organisation_id)

            if len(parts) == 3 and parts_lower[2] == "stations":
                return 200, self.get_organisation_stations(organisation_id)

            if len(parts) == 3 and parts_lower[2] == "certificates":
                return 200, self.get_organisation_certificates(organisation_id)

            if len(parts) == 5 and parts_lower[2:5:2] == ["certificates", "breakdown"]:
                return 200, self.get_organisation_certificates_breakdown(organisation_id, parts[3])

            if len(parts) == 5 and parts_lower[2:5:2] == ["certificates", "history"]:
                return 200, self.get_organisation_certificates_history(
                    organisation_id,
                    parts[3],
                    from_date=query.get("fromDate"),
                    to_date=query.get("toDate"),
                )

        if method == "GET" and parts_lower[:1] == ["stations"] and len(parts) == 2:
            return 200, self.get_station(parts[1])

        if method == "POST" and len(parts) >= 4 and parts_lower[:1] == ["organisations"] and parts_lower[-1:] == ["find-organisation"]:
            organisation_id = parts[1]
            cert_type = parts[3]
            recipient_reference = body.get("recipient_reference") or query.get("recipientReference")
            if not recipient_reference:
                return 400, {"error": "recipient_reference is required"}
            return 200, self.find_organisation(organisation_id, recipient_reference, cert_type)

        return 404, {"error": "route not found"}

    def get_user(self) -> User:
        return self.wrapper.get_user()

    def get_user_organisations(
        self,
        sort_field: str | None = None,
        sort_direction: str | None = None,
    ) -> list[OrganisationSummary]:
        return self.wrapper.get_user_organisations(sort_field=sort_field, sort_direction=sort_direction)

    def get_organisation(self, organisation_id: str) -> OrganisationDetail:
        return self.wrapper.get_organisation(organisation_id)

    def get_organisation_output_data_tasks(
        self,
        organisation_id: str,
        statuses: list[str] | None = None,
        sort_field: str | None = None,
        sort_direction: str | None = None,
        page_number: int = 1,
    ) -> OutputDataTaskList:
        return self.wrapper.get_organisation_output_data_tasks(
            organisation_id,
            statuses=statuses,
            sort_field=sort_field,
            sort_direction=sort_direction,
            page_number=page_number,
        )

    def get_organisation_station_declaration_tasks(
        self,
        organisation_id: str,
        sort_field: str | None = None,
        sort_direction: str | None = None,
        page_number: int = 1,
    ) -> StationDeclarationTaskList:
        return self.wrapper.get_organisation_station_declaration_tasks(
            organisation_id,
            sort_field=sort_field,
            sort_direction=sort_direction,
            page_number=page_number,
        )

    def get_organisation_station_declarations(self, organisation_id: str) -> StationDeclarationList:
        return self.wrapper.get_organisation_station_declarations(organisation_id)

    def get_organisation_stations(self, organisation_id: str) -> list[OrganisationStation]:
        return self.wrapper.get_organisation_stations(organisation_id)

    def get_station(self, station_id: str) -> StationDetail:
        return self.wrapper.get_station(station_id)

    def find_organisation(
        self,
        organisation_id: str,
        recipient_reference: str,
        cert_type: str = "REGO",
    ) -> OrganisationSearchResult | None:
        return self.wrapper.find_transfer_organisation(organisation_id, recipient_reference, cert_type)

    def get_organisation_certificates(self, organisation_id: str) -> CertificatesOverview:
        return self.wrapper.get_organisation_certificates(organisation_id)

    def get_organisation_certificates_breakdown(self, organisation_id: str, cert_type: str) -> CertificateBreakdown:
        return self.wrapper.get_organisation_certificates_breakdown(organisation_id, cert_type)

    def select_certificates(
        self,
        organisation_id: str,
        cert_type: str,
        station: str,
        start_period: str,
        end_period: str,
    ) -> None:
        self.wrapper.select_certificates(organisation_id, cert_type, station, start_period, end_period)

    def get_organisation_certificates_history(
        self,
        organisation_id: str,
        cert_type: str,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> CertificateHistory:
        return self.wrapper.get_organisation_certificates_history(organisation_id, cert_type, from_date, to_date)
