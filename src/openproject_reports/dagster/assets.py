"""Full-refresh reporting asset graph."""

from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from dagster import AssetExecutionContext, asset

from openproject_reports.dagster.resources import RuntimeResource
from openproject_reports.drive import find_canonical_id, publish
from openproject_reports.reporting import dataset
from openproject_reports.workbook import build_workbook


@asset
def openproject_work_packages(runtime: RuntimeResource) -> list[dict[str, Any]]:
    return runtime.openproject().work_packages()


@asset
def openproject_reporting_dataset(
    runtime: RuntimeResource, openproject_work_packages: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    settings = runtime.settings()
    return dataset(
        openproject_work_packages,
        settings.openproject_base_url,
        datetime.now(UTC),
        settings.timezone,
    )


@asset
def openproject_status_workbook(
    runtime: RuntimeResource, openproject_reporting_dataset: list[dict[str, Any]]
) -> bytes:
    settings = runtime.settings()
    file_id = find_canonical_id(
        runtime.drive_files(), settings.drive_folder_id, settings.drive_filename
    )
    return build_workbook(
        openproject_reporting_dataset,
        datetime.now(UTC).astimezone(ZoneInfo(settings.timezone)),
        settings.openproject_base_url,
        settings.timezone,
        file_id,
    )


@asset
def google_drive_openproject_report(
    context: AssetExecutionContext,
    runtime: RuntimeResource,
    openproject_status_workbook: bytes,
) -> str:
    settings = runtime.settings()
    file_id = publish(
        runtime.drive_files(),
        settings.drive_folder_id,
        settings.drive_filename,
        openproject_status_workbook,
    )
    context.log.info("Updated canonical Drive file ID: %s", file_id)
    return file_id
