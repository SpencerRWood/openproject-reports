# openproject-reports

Daily OpenProject status workbook, published to a single persistent Google Drive file.

## Data flow

`openproject_work_packages` and `openproject_projects` → `openproject_reporting_dataset` → `openproject_status_workbook` → `google_drive_openproject_report`. The `openproject_full_refresh` job runs daily at 06:00 America/New_York via `openproject_daily`. The extraction uses `/api/v3/work_packages` with `filters=[]` to disable OpenProject's default status filter and paginates through every page.

The four sheets are Work Packages, Projects, Progress, and Metadata (schema version 2). Work Packages contains only Stories, including completed and rejected Stories. Initiative/Epic IDs and subjects are resolved through the full parent hierarchy and retained as context columns; release ID/name, the legacy version column, and OpenProject URL are preserved. Projects includes visible projects with zero Stories; `total_work_packages` now counts Stories only. Initiative, Epic, Task, Spike, and Milestone statuses do not contribute to operational counts or progress.

Each refresh retrieves paginated activities only for Stories. `implementation_summary` contains the newest comment whose opening heading is `Implementation update` (including the standard `Implementation update (WP-<id>)`) or `Implementation summary`, case-insensitively, with an optional Markdown heading. Creation timestamp and activity ID determine the latest comment; later discussion and system updates are ignored. Stories without a labelled summary have a blank field. The workbook does not include activity history. Missing ancestors remain blank, and cycles terminate safely. Weekly progress uses actual completion dates only. The current open count is labeled as a run snapshot.

## Runtime settings

Infrastructure dev injects these through Infisical: `OPENPROJECT_BASE_URL`, `OPENPROJECT_API_TOKEN`, `GOOGLE_DRIVE_CREDENTIALS_JSON` (single-line authorized-user OAuth JSON with refresh token, or a delegated service-account JSON), and `GOOGLE_DRIVE_FOLDER_ID`. Set the folder ID in the runtime environment; it is not fixed in application code. For local runs, set it in a `.env` file and load that file into the process environment. Optional settings: `GOOGLE_DRIVE_FILENAME` (fixed to `OpenProject Status.xlsx`) and `REPORT_TIMEZONE` (defaults to `America/New_York`). For domain-wide delegation, include `impersonated_user` in the JSON or set `GOOGLE_DRIVE_IMPERSONATED_USER` locally; infrastructure forwards the JSON field. The target is a My Drive folder, so a plain service account cannot create the first file there.

Publisher lookup is scoped to that folder and exact name. It refuses multiple matches, creates on first run, and updates media by the existing file ID thereafter.

## Release and deployment

Pull requests use the shared `validate.yml@v3` workflow. A push to `main`
uses `release-container.yml@v3` to validate the project, build and verify the
GHCR image, then publish the semantic Git tag and GitHub Release. A successful
release passes the digest-qualified image to the separate
`promote-container-to-dev.yml@v2` contract. The application repository owns
the image; infrastructure owns the dev image pin and deployment.

## Development

`uv lock && uv sync --frozen --group dev`, then `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`, `uv run pytest`, `uv build`, and `uv run pre-commit run --all-files`.

## OpenProject planning

Initiative 407 (OpenProject Reports) in Wood Platform, Epic 408 (Reporting model enhancements), and planning release R1 (version 20) track this reporting model work.
