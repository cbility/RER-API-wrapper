# region imports
import json
from dataclasses import asdict
from typing import Any, Callable, Protocol
from datetime import datetime

import requests

from rer_api_wrapper import RERClient
from rer_api_wrapper.models import (
    CertificatesOverview,
    OrganisationStation,
    OrganisationSummary,
)
from rer_scraper.models import (
    RefreshResult,
    ScraperOperations,
    ScraperResult,
    TransferInstruction,
    TransferPreparationResult,
)
from rer_scraper.smartsuite import RERSmartSuiteClient

import logging

# endregion imports

# region configuration
logger = logging.getLogger(__name__)


class RetryInvoker(Protocol):
    """
    Protocol defining a contract for triggering retry executions of the scraper Lambda function.
    
    This is used when the session-auth API returns a 202 Accepted response, indicating that
    cookies are not yet ready. The RetryInvoker schedules an asynchronous retry of the scraper
    without blocking the current execution.
    
    The Protocol pattern allows dependency injection, enabling different implementations
    for production (Boto3RetryInvoker in handler.py) and testing (StubRetryInvoker in tests).
    """

    def invoke(
        self, function_name: str, payload: dict[str, Any]
    ) -> None:
        """
        Invoke a retry of the scraper function.
        
        Args:
            function_name: The name of the Lambda function to invoke.
            payload: The payload to pass to the function, typically including retry flags.
        """
        ...  # implemented in lambda handler


class SessionAuthClient:
    """
    Client for retrieving RER session cookies from the session-auth API.
    
    This client communicates with the session-auth Lambda service to obtain
    authenticated cookies for accessing the RER portal. When cookies are not
    yet ready (e.g., during OAuth flow), the API returns a 202 Accepted status,
    and this client returns None to signal that a retry should be scheduled.
    """

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
    """
    Main service orchestrating RER data scraping and SmartSuite synchronization.
    
    This service coordinates the following operations:
    - Retrieving session cookies via the SessionAuthClient
    - Fetching current data from RER (organisations, stations, certificates)
    - Updating SmartSuite records with the latest RER data
    - Preparing certificate transfers between organisations
    - Scheduling retries when session authentication is pending
    
    The service uses dependency injection for flexibility and testability:
    - RERSmartSuiteClient for SmartSuite API interactions
    - SessionAuthClient for RER session management
    - RetryInvoker for scheduling retry executions
    - wrapper_factory for creating RER API wrapper instances
    """

    def __init__(
        self,
        smartsuite: RERSmartSuiteClient,
        session_auth: SessionAuthClient,
        retry_invoker: RetryInvoker,
        function_name: str,
        wrapper_factory: Callable[[dict[str, str]], RERClient] = RERClient,
    ):
        self.smartsuite = smartsuite
        self.session_auth = session_auth
        self.retry_invoker = retry_invoker
        self.function_name = function_name
        self.wrapper_factory = wrapper_factory

    def run(self, schedule_retry: bool = True) -> tuple[int, ScraperResult | None]:
        run_start = datetime.now()
        operations = self.smartsuite.get_operations(run_start)
        if len(operations) == 0:
            return 204, None  # successful run but no tasks scheduled

        cookies = self.session_auth.get_cookies()
        if cookies is None:
            if schedule_retry:
                self.retry_invoker.invoke(self.function_name, {"retry_scrape": True})
            return 202, None

        rer = self.wrapper_factory(cookies)
        result = ScraperResult()
        if "refresh_data" in operations:
            organisations, stations, certificates = self.get_current_data(rer)
            self.update_rer_organisations(organisations)
            # TODO: update stations

        if "transfer_certificates" in operations:
            raise NotImplementedError

        return 200, result

    def get_current_data(self, rer: RERClient):
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
        wrapper: RERClient,
        transfer: TransferInstruction,
    ) -> TransferPreparationResult:
        source_station = wrapper.get_station(transfer.source_station_id)
        source_organisation_id = self._find_source_organisation_id(
            wrapper, transfer.source_station_id
        )
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

    def update_rer_organisations(
        self,
        organisations: list[OrganisationSummary],
    ):
        """
        Updates organisation and station records on SmartSuite with the passed details.
        Updates records if they already exist, otherwise creates new records.
        Certificate information is used to create statistics and stores at the station level.
        """

        ss_organisations = self.smartsuite.get_current_organisations()

        # spit records into updates and inserts

        update_orgs = []
        insert_orgs = []
        for org in organisations:
            ss_org_record = next(
                (
                    ss_org
                    for ss_org in ss_organisations
                    if self.smartsuite.get_organisation_id(ss_org)
                    == org.organisation_id
                ),
                None,
            )
            if ss_org_record is not None:
                update_orgs.append(
                    {**self.smartsuite.map_organisation(org), "id": ss_org_record["id"]}
                )
            else:
                insert_orgs.append(self.smartsuite.map_organisation(org))

        logger.info(
            f"Found {len(update_orgs)} orgs to be updated and {len(insert_orgs)} to be created"
        )
        logger.debug(f"Orgs to update: {update_orgs}")
        logger.debug(f"Orgs to create: {insert_orgs}")

        self.smartsuite.update_organisations(update_orgs)
        self.smartsuite.create_organisations(insert_orgs)

        # map RER fields onto smartsuite fields

    @staticmethod
    def _find_source_organisation_id(rer: RERClient, station_id: str) -> str:
        for organisation in rer.get_user_organisations():
            stations = rer.get_organisation_stations(organisation.organisation_id)
            if any(station.station_id == station_id for station in stations):
                return organisation.organisation_id
        raise ValueError(
            f"Station {station_id!r} is not available to the authenticated user."
        )


def result_body(result: ScraperResult | None) -> str:
    return json.dumps(asdict(result) if result else {})
