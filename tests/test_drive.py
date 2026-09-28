# mypy: disable-error-code="no-untyped-def,no-untyped-call,import-untyped,type-arg"
import pytest

from openproject_reports.drive import XLSX_MIME, publish


class Request:
    def __init__(self, result):
        self.result = result

    def execute(self):
        return self.result


class FakeFiles:
    def __init__(self):
        self.files = []
        self.creates = 0
        self.updates = 0

    def list(self, **kwargs):
        assert "'folder' in parents" in kwargs["q"]
        return Request({"files": list(self.files)})

    def create(self, **kwargs):
        self.creates += 1
        self.files.append(
            {"id": "stable-id", "mimeType": XLSX_MIME, "name": kwargs["body"]["name"]}
        )
        return Request({"id": "stable-id"})

    def update(self, **kwargs):
        self.updates += 1
        assert kwargs["fileId"] == "stable-id"
        return Request({"id": "stable-id"})


def test_create_once_then_update_same_id():
    files = FakeFiles()
    first = publish(files, "folder", "OpenProject Status.xlsx", b"first")
    second = publish(files, "folder", "OpenProject Status.xlsx", b"second")
    assert first == second == "stable-id"
    assert files.creates == 1
    assert files.updates == 1
    assert len(files.files) == 1


def test_duplicate_file_fails_closed():
    files = FakeFiles()
    files.files = [{"id": "a"}, {"id": "b"}]
    with pytest.raises(ValueError, match="Multiple canonical"):
        publish(files, "folder", "OpenProject Status.xlsx", b"data")
    assert files.creates == files.updates == 0


def test_wrong_mime_type_fails_closed():
    files = FakeFiles()
    files.files = [
        {"id": "stable-id", "mimeType": "application/vnd.google-apps.spreadsheet"}
    ]
    with pytest.raises(ValueError, match="unexpected MIME type"):
        publish(files, "folder", "OpenProject Status.xlsx", b"data")
    assert files.updates == files.creates == 0
