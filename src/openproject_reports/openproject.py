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
            response = self.session.get(
                f"{self.base_url}/api/v3/work_packages",
                params={"offset": offset, "pageSize": page_size},
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            elements: list[dict[str, Any]] = data.get("_embedded", {}).get(
                "elements", []
            )
            rows.extend(elements)
            total = int(data.get("total", len(rows)))
            if not elements or len(rows) >= total:
                return rows
            offset += 1
