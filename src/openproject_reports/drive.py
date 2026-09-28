"""Publish exactly one binary Excel file in a fixed Google Drive folder."""

import io
import json
from typing import Any, Protocol

from google.oauth2 import service_account
from googleapiclient.discovery import build  # type: ignore[import-untyped]
from googleapiclient.http import MediaIoBaseUpload  # type: ignore[import-untyped]

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class DriveFiles(Protocol):
    def list(self, **kwargs: Any) -> Any: ...
    def create(self, **kwargs: Any) -> Any: ...
    def update(self, **kwargs: Any) -> Any: ...


def authenticated_files(service_account_json: str) -> DriveFiles:
    info = json.loads(service_account_json)
    credentials = service_account.Credentials.from_service_account_info(
        info,
        scopes=["https://www.googleapis.com/auth/drive"],  # type: ignore[no-untyped-call]
    )
    return build("drive", "v3", credentials=credentials, cache_discovery=False).files()  # type: ignore[no-any-return]


def find_canonical_id(files: DriveFiles, folder_id: str, filename: str) -> str | None:
    """Resolve the one exact file, failing closed on duplicates."""
    escaped_name = filename.replace("\\", "\\\\").replace("'", "\\'")
    escaped_folder = folder_id.replace("\\", "\\\\").replace("'", "\\'")
    query = (
        f"name = '{escaped_name}' and '{escaped_folder}' in parents and trashed = false"
    )
    matches: list[dict[str, Any]] = []
    page_token = None
    while True:
        result = files.list(
            q=query,
            fields="nextPageToken, files(id,name,mimeType,parents)",
            pageSize=1000,
            pageToken=page_token,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()
        matches.extend(result.get("files", []))
        page_token = result.get("nextPageToken")
        if not page_token:
            break
    if len(matches) > 1:
        raise ValueError("Multiple canonical report files exist; refusing to publish")
    if matches and matches[0].get("mimeType") != XLSX_MIME:
        raise ValueError("Canonical file has an unexpected MIME type")
    return str(matches[0]["id"]) if matches else None


def publish(files: DriveFiles, folder_id: str, filename: str, contents: bytes) -> str:
    """Create once or update the existing ID without a replacement."""
    existing_id = find_canonical_id(files, folder_id, filename)
    media = MediaIoBaseUpload(io.BytesIO(contents), mimetype=XLSX_MIME, resumable=True)
    if existing_id:
        result = files.update(
            fileId=existing_id,
            media_body=media,
            fields="id",
            supportsAllDrives=True,
        ).execute()
        if result["id"] != existing_id:
            raise ValueError("Drive update returned a different file ID")
        return existing_id
    result = files.create(
        body={"name": filename, "parents": [folder_id], "mimeType": XLSX_MIME},
        media_body=media,
        fields="id",
        supportsAllDrives=True,
    ).execute()
    return str(result["id"])
