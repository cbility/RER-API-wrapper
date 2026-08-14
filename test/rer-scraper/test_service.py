from __future__ import annotations

from dataclasses import dataclass

from rer_scraper.models import ScraperOperations, TransferInstruction
from rer_scraper.service import RERScraperService


class StubSmartSuiteClient:
    def __init__(self, operations: ScraperOperations):
        self.operations = operations

    def get_operations(self) -> ScraperOperations:
        return self.operations


class StubSessionAuthClient:
    def __init__(self, cookies: dict[str, str] | None):
        self.cookies = cookies

    def get_cookies(self) -> dict[str, str] | None:
        return self.cookies


class StubRetryInvoker:
    def __init__(self):
        self.function_name: str | None = None
        self.payload: dict[str, bool] | None = None

    def invoke(self, function_name: str, payload: dict[str, bool]) -> None:
        self.function_name = function_name
        self.payload = payload


def make_service(
    operations: ScraperOperations,
    cookies: dict[str, str] | None,
    retry_invoker: StubRetryInvoker,
) -> RERScraperService:
    return RERScraperService(
        smartsuite=StubSmartSuiteClient(operations),  # type: ignore[arg-type]
        session_auth=StubSessionAuthClient(cookies),  # type: ignore[arg-type]
        retry_invoker=retry_invoker,
        function_name="scraper-function",
    )


def test_exits_early_without_operations():
    retry_invoker = StubRetryInvoker()
    service = make_service(ScraperOperations(), {"session": "cached"}, retry_invoker)

    status_code, result = service.run()

    assert status_code == 204
    assert result is None
    assert retry_invoker.function_name is None


def test_schedules_retry_when_session_auth_is_refreshing():
    retry_invoker = StubRetryInvoker()
    service = make_service(ScraperOperations(refresh_data=True), None, retry_invoker)

    status_code, result = service.run()

    assert status_code == 202
    assert result is None
    assert retry_invoker.function_name == "scraper-function"
    assert retry_invoker.payload == {"retry_scrape": True}


def test_does_not_schedule_nested_retry_for_async_execution():
    retry_invoker = StubRetryInvoker()
    service = make_service(ScraperOperations(refresh_data=True), None, retry_invoker)

    status_code, result = service.run(schedule_retry=False)

    assert status_code == 202
    assert result is None
    assert retry_invoker.function_name is None


@dataclass
class StubStation:
    station_id: str
    station_name: str


@dataclass
class StubStationList:
    stations: list[StubStation]


@dataclass
class StubOrganisation:
    organisation_id: str
    name: str = "Organisation"


class StubWrapper:
    def __init__(self):
        self.select_arguments: tuple[object, ...] | None = None

    def get_user_organisations(self) -> list[StubOrganisation]:
        return [StubOrganisation("GEN1")]

    def get_organisation_stations(self, organisation_id: str) -> StubStationList:
        assert organisation_id == "GEN1"
        return StubStationList([StubStation("STATION1", "Wind Farm")])

    def get_station(self, station_id: str) -> StubStation:
        return StubStation(station_id, "Wind Farm")

    def find_transfer_organisation(self, organisation_id: str, recipient_reference: str, cert_type: str):
        return object()

    def select_certificates(self, *arguments: object) -> None:
        self.select_arguments = arguments


def test_prepares_inclusive_transfer_range():
    wrapper = StubWrapper()
    service = make_service(ScraperOperations(), {"session": "cached"}, StubRetryInvoker())
    transfer = TransferInstruction("STATION1", "GEN2", "Apr 2025", "Jun 2025")

    result = service.prepare_transfer(wrapper, transfer)  # type: ignore[arg-type]

    assert result.selected is True
    assert wrapper.select_arguments == ("GEN1", "REGO", "Wind Farm", "Apr 2025", "Jun 2025")


def test_treats_missing_certificate_ranges_as_successful_no_op():
    class NoMatchWrapper(StubWrapper):
        def select_certificates(self, *arguments: object) -> None:
            raise ValueError("No REGO certificate ranges match station 'Wind Farm' between 'Apr 2025' and 'Jun 2025'.")

    service = make_service(ScraperOperations(), {"session": "cached"}, StubRetryInvoker())
    result = service.prepare_transfer(
        NoMatchWrapper(),  # type: ignore[arg-type]
        TransferInstruction("STATION1", "GEN2", "Apr 2025", "Jun 2025"),
    )

    assert result.selected is False
    assert result.reason == "no matching certificate ranges"