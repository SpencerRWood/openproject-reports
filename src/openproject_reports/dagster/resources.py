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
        return authenticated_files(self.settings().google_service_account_json)
