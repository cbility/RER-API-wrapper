from __future__ import annotations

import os
from smartsuite_python import SmartSuiteClient, FilterElement, FilterDateValue, FilterDateMode
from dataclasses import asdict
from datetime import datetime

from rer_api_wrapper.models import CertificatesOverview, OrganisationStation, OrganisationSummary
from rer_scraper.models import ScraperOperations


class RERSmartSuiteClient(SmartSuiteClient):
    """Owns SmartSuite HTTP access and scraper-specific record mappings."""

    # record ids
    record_id_rer_scaper = "6a7104dc65c1e43caf1f2792", # smartsuite record ID belonging to the record for the scraper

    # table ids
    table_id_scraper_job_configuration_table_id = "663d2313b4e7828a33b1ac07"
    table_id_ro_organisations = "665dc5a9eb40433ff6407de9"
    table_id_ro_stations = "652b1faba9847148f31cee2a"

    def __init__(self, account_id: str, api_token: str):
        self.ss = SmartSuiteClient(account_id, api_token)

    @classmethod
    def from_env(cls) -> "RERSmartSuiteClient":
        account_id = os.getenv("SMARTSUITE_ACCOUNT_ID")
        if account_id is None:
            raise ValueError("SMARTSUITE_ACCOUNT_ID is not included in .env file.")
        
        api_token = os.getenv("SMARTSUITE_API_TOKEN")
        if api_token is None:
            raise ValueError("SMARTSUITE_API_TOKEN is not included in .env file.")
        
        return cls(
            account_id=account_id,
            api_token=api_token,
        )

    def get_operations(self, launch_time: datetime) -> list[ScraperOperations]:
        """Return pending scraper work once the SmartSuite schema is configured."""
        scraper_filter = FilterElement(
            field="s902579400", # Scraper field
            comparison= "is",
            value="6a7104dc65c1e43caf1f2792" # RER Scraper record ID
        )
        next_run_filter = FilterElement(
            field= "s8173a46ec", # Run Next After field
            comparison = "is_on_or_after",
            value = FilterDateValue(date_mode="exact_date", date_mode_value=launch_time.isoformat())
        )
        operations_records = self.ss.filter_records(table_id="663d2313b4e7828a33b1ac07", # Scraper job configuration table
                               fields_to_filter=[scraper_filter, next_run_filter])

        operations: list[ScraperOperations] = []

        for record in operations_records:
            match (record["id"]):
                case "6a8328cb2f59c6c95139943d": # data update record id
                    operations.append("refresh_data")
                case "6a832d732f59c6c951399446": # certificate transfer record id
                    operations.append("transfer_certificates")

        return operations

    def get_current_organisations(self):
        current_organisations = self.ss.get_all_records(table_id = self.table_id_ro_organisations)
        return current_organisations

    def get_current_stations(self):
            current_organisations = self.ss.get_all_records(table_id = self.table_id_ro_stations)
            return current_organisations

    def update_rer_data(self,
                        organisations: list[OrganisationSummary],
                        stations: list[OrganisationStation], 
                        certificates: list[CertificatesOverview]
        ):
        """
        Updates organisation and station records on SmartSuite with the passed details.
        Updates records if they already exist, otherwise creates new records.
        Certificate information is used to create statistics and stores at the station level.
        """

        raise NotImplementedError("This method is not yet implemented.")
    
        org_id_field = "s44395f753" # Organisation reference

        ss_organisations = self.get_current_organisations()
        ss_stations = self.get_current_stations()

        
        existing_orgs = []
        non_existing_orgs = []
        for org in organisations:
            if org.organisation_id in [ss_org[org_id_field] for ss_org in ss_organisations]:
                existing_orgs.append(org)
            else:
                non_existing_orgs.append(org)

        existing_stations = []
        non_existing_stations = []
        for station in stations:
            if station


