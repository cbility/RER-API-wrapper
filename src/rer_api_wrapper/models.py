from __future__ import annotations

from typing import Any

from pydantic.dataclasses import dataclass


@dataclass
class RERModel:
    def __getitem__(self, key: str):
        return getattr(self, key)


@dataclass
class RERRequest(RERModel):
    method: str
    path: str
    query: dict[str, Any]
    body: dict[str, Any]
    cookies: dict[str, str]


@dataclass
class OrganisationSummary(RERModel):
    organisation_id: str
    name: str
    type: str
    task_count: int
    status: str
    user_status: str


@dataclass
class User(RERModel):
    email: str
    full_name: str
    outstanding_tasks: int
    active_organisations: int


@dataclass
class OrganisationAddress(RERModel):
    name: str
    address: str


@dataclass
class OrganisationContact(RERModel):
    name: str
    email: str


@dataclass
class OrganisationTab(RERModel):
    name: str
    url: str


@dataclass
class OrganisationDetail(RERModel):
    organisation_id: str
    name: str
    type: str
    status: str
    address: OrganisationAddress
    contact: OrganisationContact
    tabs: list[OrganisationTab]


@dataclass
class OutputDataTask(RERModel):
    task_id: str
    period: str
    station_name: str
    status: str
    url: str


@dataclass
class OutputDataTaskList(RERModel):
    organisation_id: str
    tasks: list[OutputDataTask]


@dataclass
class StationDeclarationTask(RERModel):
    declaration_type: str
    year: str
    url: str


@dataclass
class StationDeclarationTaskList(RERModel):
    organisation_id: str
    tasks: list[StationDeclarationTask]


@dataclass
class StationDeclaration(RERModel):
    declaration_type: str
    period: str
    status: str
    url: str


@dataclass
class StationDeclarationList(RERModel):
    organisation_id: str
    declarations: list[StationDeclaration]


@dataclass
class StationSchemeStatus(RERModel):
    scheme: str
    status: str


@dataclass
class OrganisationStation(RERModel):
    station_id: str
    station_name: str
    organisation_id: str
    organisation_name: str
    country: str
    technology_group: str
    scheme_statuses: list[StationSchemeStatus]
    last_updated: str
    url: str


@dataclass
class SchemeAccreditation(RERModel):
    scheme: str
    accreditation_reference: str
    application_date: str
    effective_from: str
    status: str


@dataclass
class StationCapacity(RERModel):
    capacity_type: str
    commissioning_date: str
    date_added: str
    tic: str
    dnc: str


@dataclass
class StationDetail(RERModel):
    station_id: str
    station_name: str
    organisation_name: str
    country: str
    commissioning_date: str
    total_installed_capacity: str
    technology_group: str
    prelim_approval: str
    address: str
    grid_reference: str
    application_date: str
    declared_net_capacity: str
    roofit_technology: str
    rego_technology: str
    connected_to_network: str
    will_export: str
    export_connection_capacity: str
    station_description: str
    has_battery_storage: str
    has_standby_generator: str
    scheme: str
    rego_accredited: str
    output_submission_frequency: str
    scheme_accreditations: list[SchemeAccreditation]
    station_capacities: list[StationCapacity]


@dataclass
class OrganisationSearchResult(RERModel):
    reference: str
    name: str


@dataclass
class CertificateTypeSummary(RERModel):
    cert_type: str
    issued: int
    balance: int | None
    breakdown_url: str
    history_url: str


@dataclass
class CertificatesOverview(RERModel):
    organisation_id: str
    balance_period: str
    summaries: list[CertificateTypeSummary]


@dataclass
class CertificateBreakdownItem(RERModel):
    action: str
    country: str
    station: str
    technology: str
    output_period: str
    count: int


@dataclass
class CertificateBreakdown(RERModel):
    organisation_id: str
    cert_type: str
    items: list[CertificateBreakdownItem]


@dataclass
class CertificateHistoryMonth(RERModel):
    month: str
    month_url: str
    transferred_in: int
    transferred_out: int


@dataclass
class CertificateHistory(RERModel):
    organisation_id: str
    cert_type: str
    months: list[CertificateHistoryMonth]
