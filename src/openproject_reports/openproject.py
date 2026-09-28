"""Complete, unfiltered OpenProject work-package extraction."""

from typing import Any

import requests


class OpenProjectClient:
    def __init__(
        self, base_url: str, token: str, session: requests.Session | None = None
    ):
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.session.auth = ("apikey", token)

    def work_packages(self, page_size: int = 100) -> list[dict[str, Any]]:
        return self._collection(
            "work_packages", page_size, {"filters": "[]", "sortBy": '[["id","asc"]]'}
        )

    def projects(self, page_size: int = 100) -> list[dict[str, Any]]:
        return [
            item
            for item in self._collection(
                "projects",
                page_size,
                {"filters": "[]", "sortBy": '[["id","asc"]]'},
            )
            if item.get("_type", "Project") == "Project"
        ]

    def _collection(
        self, endpoint: str, page_size: int, extra_params: dict[str, str]
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        offset = 1
        while True:
            params: dict[str, str | int] = {
                "offset": offset,
                "pageSize": page_size,
                **extra_params,
            }
            response = self.session.get(
                f"{self.base_url}/api/v3/{endpoint}",
                params=params,
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            elements: list[dict[str, Any]] = data.get("_embedded", {}).get(
                "elements", []
            )
            rows.extend(elements)
            total = int(data.get("total", len(rows)))
            if len(rows) >= total:
                return rows
            if not elements:
                raise ValueError("OpenProject returned an incomplete collection")
            offset += 1
