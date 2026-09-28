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
        rows: list[dict[str, Any]] = []
        offset = 1
        while True:
            params: dict[str, str | int] = {
                "offset": offset,
                "pageSize": page_size,
                "filters": "[]",
                "sortBy": '[["id","asc"]]',
            }
            response = self.session.get(
                f"{self.base_url}/api/v3/work_packages",
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
                raise ValueError(
                    "OpenProject returned an incomplete work package collection"
                )
            offset += 1
