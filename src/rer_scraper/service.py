from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Callable, Protocol

import requests

from rer_api_wrapper import RER_wrapper
from rer_scraper.models import (
    RefreshResult,
    ScraperOperations,
    ScraperResult,
    TransferInstruction,
    TransferPreparationResult,
)
from rer_scraper.smartsuite import SmartSuiteClient

import logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RetryInvoker(Protocol):
    def invoke(self, function_name: str, payload: dict[str, Any]) -> None:
        ...


class SessionAuthClient:
    def __init__(self, api_url: str, api_key: str, timeout: int = 30):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def get_cookies(self) -> dict[str, str] | None:
        response = requests.get(
            self.api_url,
            headers={"x-api-key": self.api_key},
            timeout=self.timeout,
        )
        if response.status_code == 202:
            return None
        response.raise_for_status()
        cookies = response.json().get("cookies")
        if not isinstance(cookies, dict):
            raise ValueError("Session-auth API response did not include cookies.")
        return {str(name): str(value) for name, value in cookies.items()}


class RERScraperService:
    def __init__(
        self,
        smartsuite: SmartSuiteClient,
        session_auth: SessionAuthClient,
        retry_invoker: RetryInvoker,
        function_name: str,
        wrapper_factory: Callable[[dict[str, str]], RER_wrapper] = RER_wrapper,
    ):
        self.smartsuite = smartsuite
        self.session_auth = session_auth
        self.retry_invoker = retry_invoker
        self.function_name = function_name
        self.wrapper_factory = wrapper_factory

    def run(self, schedule_retry: bool = True) -> tuple[int, ScraperResult | None]:
        operations = self.smartsuite.get_operations()
        if not operations.has_work:
            return 204, None

        cookies = self.session_auth.get_cookies()
        if cookies is None:
            if schedule_retry:
                self.retry_invoker.invoke(self.function_name, {"retry_scrape": True})
            return 202, None

        rer = self.wrapper_factory(cookies)
        result = ScraperResult()
        if operations.refresh_data:
            organisations, stations, certificates = self.refresh_data(rer)
        result.transfer_results = [self.prepare_transfer(rer, transfer) for transfer in operations.transfers]
        return 200, result

    def refresh_data(self, rer: RER_wrapper):
        organisations = rer.get_user_organisations()
        logger.debug(organisations)
        organisation_stations = [
            rer.get_organisation_stations(organisation.organisation_id)
            for organisation in organisations
        ]
        logger.debug(organisation_stations)
        organisation_certificates = [
             rer.get_organisation_certificates(organisation.organisation_id)
            for organisation in organisations
        ]
        logger.debug(organisation_certificates)

        return organisations, organisation_stations, organisation_certificates

    def prepare_transfer(
        self,
        wrapper: RER_wrapper,
        transfer: TransferInstruction,
    ) -> TransferPreparationResult:
        source_station = wrapper.get_station(transfer.source_station_id)
        source_organisation_id = self._find_source_organisation_id(wrapper, transfer.source_station_id)
        recipient = wrapper.find_transfer_organisation(
            source_organisation_id,
            transfer.destination_generator_reference,
            transfer.certificate_type,
        )
        if recipient is None:
            return TransferPreparationResult(
                source_station_id=transfer.source_station_id,
                destination_generator_reference=transfer.destination_generator_reference,
                selected=False,
                reason="destination generator was not found",
            )

        try:
            wrapper.select_certificates(
                source_organisation_id,
                transfer.certificate_type,
                source_station.station_name,
                transfer.start_period,
                transfer.end_period,
            )
        except ValueError as exc:
            if str(exc).startswith("No ") and "certificate ranges match" in str(exc):
                return TransferPreparationResult(
                    source_station_id=transfer.source_station_id,
                    destination_generator_reference=transfer.destination_generator_reference,
                    selected=False,
                    reason="no matching certificate ranges",
                )
            raise

        return TransferPreparationResult(
            source_station_id=transfer.source_station_id,
            destination_generator_reference=transfer.destination_generator_reference,
            selected=True,
        )

    @staticmethod
    def _find_source_organisation_id(rer: RER_wrapper, station_id: str) -> str:
        for organisation in rer.get_user_organisations():
            stations = rer.get_organisation_stations(organisation.organisation_id)
            if any(station.station_id == station_id for station in stations.stations):
                return organisation.organisation_id
        raise ValueError(f"Station {station_id!r} is not available to the authenticated user.")


def result_body(result: ScraperResult | None) -> str:
    return json.dumps(asdict(result) if result else {})

