# mypy: disable-error-code="no-untyped-def,no-untyped-call,import-untyped,type-arg"
from datetime import UTC, datetime
from io import BytesIO

import pytest
from openpyxl import load_workbook

from openproject_reports.config import load_config
from openproject_reports.dagster.definitions import defs
from openproject_reports.openproject import OpenProjectClient
from openproject_reports.reporting import dataset, progress, projects
from openproject_reports.workbook import build_workbook

NOW = datetime(2026, 9, 28, 12, tzinfo=UTC)


def package(
    identifier: int, status: str, updated: str = "2026-09-20T00:00:00Z"
) -> dict:
    return {
        "id": identifier,
        "subject": f"Work {identifier}",
        "createdAt": "2026-09-01T00:00:00Z",
        "updatedAt": updated,
        "closedAt": "2026-09-22T00:00:00Z" if status == "Closed" else None,
        "_links": {
            "project": {"href": "/api/v3/projects/2", "title": "Project B"},
            "status": {"title": status},
            "type": {"title": "Task"},
        },
    }


class Response:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


class Session:
    def __init__(self):
        self.offsets = []

    def get(self, url, params, timeout):
        assert url.endswith("/work_packages")
        assert timeout == 60
        self.offsets.append(params["offset"])
        identifier = params["offset"]
        return Response(
            {"total": 2, "_embedded": {"elements": [package(identifier, "Closed")]}}
        )


def test_pagination_retains_completed():
    session = Session()
    rows = OpenProjectClient("https://example.test", "token", session).work_packages(1)  # type: ignore[arg-type]
    assert session.offsets == [1, 2]
    assert [row["id"] for row in rows] == [1, 2]


def test_dataset_rollups_and_workbook():
    rows = dataset(
        [package(2, "Closed"), package(1, "In Progress"), package(2, "Closed")],
        "https://example.test",
        NOW,
        "America/New_York",
    )
    assert [row["work_package_id"] for row in rows] == [1, 2]
    assert rows[1]["is_complete"] is True
    assert rows[1]["days_to_complete"] == 21
    assert rows[1]["completed_week"] == "2026-W39"
    assert rows[0]["is_open"] is True
    assert projects(rows, NOW.date())[0]["completed"] == 1
    assert progress(rows, NOW.date())[0]["cumulative_completions"] == 1
    book = load_workbook(
        BytesIO(build_workbook(rows, NOW, "https://example.test", "America/New_York"))
    )
    assert book.sheetnames == ["Work Packages", "Projects", "Progress", "Metadata"]
    assert book["Work Packages"].max_row == 3
    assert book["Work Packages"].freeze_panes == "A2"
    assert book["Work Packages"].auto_filter.ref == book["Work Packages"].dimensions


def test_config_validation():
    with pytest.raises(ValueError, match="Missing runtime settings"):
        load_config({})
    settings = load_config(
        {
            "OPENPROJECT_BASE_URL": "https://example.test/",
            "OPENPROJECT_API_TOKEN": "secret",
            "GOOGLE_SERVICE_ACCOUNT_JSON": "{}",
            "GOOGLE_DRIVE_FOLDER_ID": "folder",
        }
    )
    assert settings.openproject_base_url == "https://example.test"


def test_definitions_registered():
    assert len(defs.resolve_asset_graph().get_all_asset_keys()) == 4
    assert defs.get_job_def("openproject_full_refresh")
    assert defs.get_schedule_def("openproject_daily")
