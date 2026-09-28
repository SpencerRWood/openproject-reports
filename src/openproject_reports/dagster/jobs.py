"""Complete report refresh job."""

from dagster import define_asset_job, in_process_executor

openproject_full_refresh = define_asset_job(
    "openproject_full_refresh", executor_def=in_process_executor
)
