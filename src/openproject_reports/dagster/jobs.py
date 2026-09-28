"""Complete report refresh job."""

from dagster import define_asset_job

openproject_full_refresh = define_asset_job("openproject_full_refresh")
