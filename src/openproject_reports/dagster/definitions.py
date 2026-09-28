"""Importable code location for the shared Beelink Dagster deployment."""

from dagster import Definitions, mem_io_manager

from openproject_reports.dagster.assets import (
    google_drive_openproject_report,
    openproject_reporting_dataset,
    openproject_status_workbook,
    openproject_work_packages,
)
from openproject_reports.dagster.jobs import openproject_full_refresh
from openproject_reports.dagster.resources import RuntimeResource
from openproject_reports.dagster.schedules import openproject_daily

defs = Definitions(
    assets=[
        openproject_work_packages,
        openproject_reporting_dataset,
        openproject_status_workbook,
        google_drive_openproject_report,
    ],
    jobs=[openproject_full_refresh],
    schedules=[openproject_daily],
    resources={"runtime": RuntimeResource(), "io_manager": mem_io_manager},
)
