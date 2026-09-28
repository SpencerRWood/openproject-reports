"""Lazily loaded runtime resources so Definitions load without credentials."""

from dagster import ConfigurableResource

from openproject_reports.config import AppConfig, load_config
from openproject_reports.drive import DriveFiles, authenticated_files
from openproject_reports.openproject import OpenProjectClient


class RuntimeResource(ConfigurableResource["RuntimeResource"]):
    def settings(self) -> AppConfig:
        return load_config()

    def openproject(self) -> OpenProjectClient:
        settings = self.settings()
        return OpenProjectClient(
            settings.openproject_base_url, settings.openproject_api_token
        )

    def drive_files(self) -> DriveFiles:
        settings = self.settings()
        return authenticated_files(
            settings.google_drive_credentials_json,
            settings.google_drive_impersonated_user,
        )
