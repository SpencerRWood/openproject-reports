# Repository Guidance

- Preserve the single canonical Drive file ID; fail on duplicate names.
- Keep full refreshes inclusive of completed work packages.
- Keep credentials in Infisical and inject them through infrastructure dev.
- Validate with uv lock, uv sync --frozen --group dev, Ruff, mypy, pytest, uv build, and pre-commit.
- Dagster assets and schedule belong here; code-location deployment belongs in infrastructure.
