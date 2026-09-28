# openproject-reports

Daily OpenProject status workbook, published to a single persistent Google Drive file.

## Data flow

`openproject_work_packages` and `openproject_projects` → `openproject_reporting_dataset` → `openproject_status_workbook` → `google_drive_openproject_report`. The `openproject_full_refresh` job runs daily at 06:00 America/New_York via `openproject_daily`. The extraction uses `/api/v3/work_packages` with `filters=[]` to disable OpenProject's default status filter and paginates through every page.

The four sheets are Work Packages, Projects, Progress, and Metadata. Projects includes visible projects with zero work packages. Weekly progress uses actual completion dates only. The current open count is labeled as a run snapshot.

## Runtime settings

Infrastructure dev injects these through Infisical: `OPENPROJECT_BASE_URL`, `OPENPROJECT_API_TOKEN`, `GOOGLE_SERVICE_ACCOUNT_JSON` (service account JSON with access to the target folder), and `GOOGLE_DRIVE_FOLDER_ID`. Optional settings: `GOOGLE_DRIVE_FILENAME` (fixed to `OpenProject Status.xlsx`) and `REPORT_TIMEZONE` (defaults to `America/New_York`). Share Reports/OpenProject with the service account and grant write access. The target folder ID is `1PbcC0x4YL3CnQ02f2cmZkKOkJrhjXZMp`.

Publisher lookup is scoped to that folder and exact name. It refuses multiple matches, creates on first run, and updates media by the existing file ID thereafter.

## Development

`uv lock && uv sync --frozen --group dev`, then `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`, `uv run pytest`, `uv build`, and `uv run pre-commit run --all-files`.
