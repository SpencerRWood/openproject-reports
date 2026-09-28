"""Validated, typed runtime settings. Secrets are supplied by the deployment."""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


@dataclass(frozen=True)
class AppConfig:
    openproject_base_url: str
    openproject_api_token: str
    google_service_account_json: str
    drive_folder_id: str
    drive_filename: str
    timezone: str


def load_config(environ: Mapping[str, str] | None = None) -> AppConfig:
    values = os.environ if environ is None else environ
    required = (
        "OPENPROJECT_BASE_URL",
        "OPENPROJECT_API_TOKEN",
        "GOOGLE_SERVICE_ACCOUNT_JSON",
        "GOOGLE_DRIVE_FOLDER_ID",
    )
    missing = [key for key in required if not values.get(key)]
    if missing:
        raise ValueError(f"Missing runtime settings: {', '.join(missing)}")
    base_url = values["OPENPROJECT_BASE_URL"].rstrip("/")
    if not base_url.startswith("https://"):
        raise ValueError("OPENPROJECT_BASE_URL must use HTTPS")
    timezone = values.get("REPORT_TIMEZONE", "America/New_York")
    try:
        ZoneInfo(timezone)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("REPORT_TIMEZONE is invalid") from exc
    filename = values.get("GOOGLE_DRIVE_FILENAME", "OpenProject Status.xlsx")
    if filename != "OpenProject Status.xlsx":
        raise ValueError("GOOGLE_DRIVE_FILENAME must be OpenProject Status.xlsx")
    return AppConfig(
        openproject_base_url=base_url,
        openproject_api_token=values["OPENPROJECT_API_TOKEN"],
        google_service_account_json=values["GOOGLE_SERVICE_ACCOUNT_JSON"],
        drive_folder_id=values["GOOGLE_DRIVE_FOLDER_ID"],
        drive_filename=filename,
        timezone=timezone,
    )
