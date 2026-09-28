# mypy: disable-error-code="no-untyped-def,no-untyped-call,import-untyped,type-arg"
import json
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
        assert params["filters"] == "[]"
        assert params["sortBy"] == '[["id","asc"]]'
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


def test_project_catalog_paginates_and_excludes_non_projects():
    class ProjectSession(Session):
        def get(self, url, params, timeout):
            assert url.endswith("/projects")
            assert timeout == 60
            assert params["filters"] == "[]"
            self.offsets.append(params["offset"])
            identifier = params["offset"]
            item_type = "Project" if identifier == 1 else "Program"
            return Response(
                {
                    "total": 2,
                    "_embedded": {
                        "elements": [
                            {
                                "id": identifier,
                                "name": f"P{identifier}",
                                "_type": item_type,
                            }
                        ]
                    },
                }
            )

    session = ProjectSession()
    rows = OpenProjectClient("https://example.test", "token", session).projects(1)  # type: ignore[arg-type]
    assert session.offsets == [1, 2]
    assert [row["name"] for row in rows] == ["P1"]


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
    assert (
        projects(
            rows,
            NOW.date(),
            [{"id": 2, "name": "Project B"}, {"id": 3, "name": "Empty"}],
        )[1]["total_work_packages"]
        == 0
    )
    assert progress(rows, NOW.date())[0]["cumulative_completions"] == 1
    book = load_workbook(
        BytesIO(build_workbook(rows, NOW, "https://example.test", "America/New_York"))
    )
    assert book.sheetnames == ["Work Packages", "Projects", "Progress", "Metadata"]
    assert book["Work Packages"].max_row == 3
    catalog_book = load_workbook(
        BytesIO(
            build_workbook(
                rows,
                NOW,
                "https://example.test",
                "America/New_York",
                project_catalog=[
                    {"id": 2, "name": "Project B"},
                    {"id": 3, "name": "Empty"},
                ],
            )
        )
    )
    assert catalog_book["Projects"].max_row == 3
    assert book["Work Packages"].freeze_panes == "A2"
    assert book["Work Packages"].auto_filter.ref == book["Work Packages"].dimensions


def test_config_validation():
    with pytest.raises(ValueError, match="Missing runtime settings"):
        load_config({})
    settings = load_config(
        {
            "OPENPROJECT_BASE_URL": "https://example.test/",
            "OPENPROJECT_API_TOKEN": "secret",
            "GOOGLE_DRIVE_CREDENTIALS_JSON": json.dumps(
                {
                    "type": "authorized_user",
                    "client_id": "a",
                    "client_secret": "b",
                    "refresh_token": "c",
                }
            ),
            "GOOGLE_DRIVE_FOLDER_ID": "folder",
        }
    )
    assert settings.openproject_base_url == "https://example.test"
    with pytest.raises(ValueError, match="My Drive needs user OAuth"):
        load_config(
            {
                "OPENPROJECT_BASE_URL": "https://example.test",
                "OPENPROJECT_API_TOKEN": "secret",
                "GOOGLE_DRIVE_CREDENTIALS_JSON": json.dumps(
                    {"type": "service_account"}
                ),
                "GOOGLE_DRIVE_FOLDER_ID": "folder",
            }
        )


def test_definitions_registered():
    assert len(defs.resolve_asset_graph().get_all_asset_keys()) == 5
    assert defs.get_job_def("openproject_full_refresh")
    assert defs.get_schedule_def("openproject_daily")
