# Repository Guidance

## Branching strategy

- This repository uses **release-branch integration**. Create Story branches from the verified active `release/vX.Y.Z` and target Story PRs there; `main` changes only after the release readiness gate.
- Follow the [canonical branching and delivery policy](https://github.com/SpencerRWood/codex-config/blob/main/docs/branching-policy.md), available through the installed codex-config source path. Verify the strategy, release association, fetched base and PR target before implementation and record them in Story evidence. Story completion does not authorize publication or deployment; retain existing review, CI, security and rollback requirements.

- Preserve the single canonical Drive file ID; fail on duplicate names.
- Keep full refreshes inclusive of completed work packages.
- Keep credentials in Infisical and inject them through infrastructure dev.
- Validate with uv lock, uv sync --frozen --group dev, Ruff, mypy, pytest, uv build, and pre-commit.
- Dagster assets and schedule belong here; code-location deployment belongs in infrastructure.
