from __future__ import annotations

import os
from smartsuite_python import SmartSuiteClient, FilterElement, FilterDateValue, FilterDateMode
from dataclasses import asdict
from typing import Any, Literal, Sequence

from rer_scraper.models import ScraperOperations

class RERSmartSuiteClient(SmartSuiteClient):
    """Owns SmartSuite HTTP access and scraper-specific record mappings."""

    record_ids = {
        "rer_scaper": "6a7104dc65c1e43caf1f2792", # smartsuite record ID belonging to the record for the scraper
    }
    table_ids = {
        "scraper_job_configuration": "663d2313b4e7828a33b1ac07",
    }

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

    def get_operations(self) -> ScraperOperations:
        """Return pending scraper work once the SmartSuite schema is configured."""
        raise NotImplementedError
        scraper_filter = {
            "field": "s902579400", # Scraper field
            "comparison": "is",
            "value": "6a7104dc65c1e43caf1f2792" # RER Scraper record ID
        }
        next_run_filter = FilterElement(
                    field= "s8173a46ec", # Run Next After field
                    comparison = "is",
                    value = {"date_mode":"today", "date_mode_value":""}
        )
        self.ss.filter_records(table_id="663d2313b4e7828a33b1ac07", # Scraper job configuration table
                               fields_to_filter=[scraper_filter, next_run_filter])
        return ScraperOperations()
