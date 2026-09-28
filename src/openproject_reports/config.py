"""Validated, typed runtime settings. Secrets are supplied by the deployment."""

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


@dataclass(frozen=True)
class AppConfig:
    openproject_base_url: str
    openproject_api_token: str
    google_drive_credentials_json: str
    google_drive_impersonated_user: str | None
    drive_folder_id: str
    drive_filename: str
    timezone: str


def load_config(environ: Mapping[str, str] | None = None) -> AppConfig:
    values = os.environ if environ is None else environ
    required = (
        "OPENPROJECT_BASE_URL",
        "OPENPROJECT_API_TOKEN",
        "GOOGLE_DRIVE_CREDENTIALS_JSON",
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
    try:
        credentials = json.loads(values["GOOGLE_DRIVE_CREDENTIALS_JSON"])
    except json.JSONDecodeError as exc:
        raise ValueError("GOOGLE_DRIVE_CREDENTIALS_JSON is invalid JSON") from exc
    credential_type = credentials.get("type") if isinstance(credentials, dict) else None
    impersonated_user = values.get("GOOGLE_DRIVE_IMPERSONATED_USER") or (
        credentials.get("impersonated_user") if isinstance(credentials, dict) else None
    )
    if credential_type == "authorized_user":
        required_auth = {"client_id", "client_secret", "refresh_token"}
    elif credential_type == "service_account" and impersonated_user:
        required_auth = {"client_email", "private_key", "token_uri"}
    else:
        raise ValueError("My Drive needs user OAuth or a delegated service account")
    if not required_auth.issubset(credentials):
        raise ValueError("Google Drive credential fields are incomplete")
    return AppConfig(
        openproject_base_url=base_url,
        openproject_api_token=values["OPENPROJECT_API_TOKEN"],
        google_drive_credentials_json=values["GOOGLE_DRIVE_CREDENTIALS_JSON"],
        google_drive_impersonated_user=impersonated_user,
        drive_folder_id=values["GOOGLE_DRIVE_FOLDER_ID"],
        drive_filename=filename,
        timezone=timezone,
    )
