"""Daily local-time refresh schedule."""

from dagster import DefaultScheduleStatus, ScheduleDefinition

from openproject_reports.dagster.jobs import openproject_full_refresh

openproject_daily = ScheduleDefinition(
    name="openproject_daily",
    job=openproject_full_refresh,
    cron_schedule="0 6 * * *",
    execution_timezone="America/New_York",
    default_status=DefaultScheduleStatus.RUNNING,
)
