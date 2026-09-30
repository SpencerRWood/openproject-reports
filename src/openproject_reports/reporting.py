"""Canonical rows and factual progress rollups."""

import re
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

FIELDS = (
    "work_package_id",
    "project_id",
    "project",
    "subject",
    "description",
    "type",
    "status",
    "priority",
    "assignee",
    "parent_id",
    "version",
    "release_id",
    "release",
    "initiative_id",
    "initiative",
    "epic_id",
    "epic",
    "implementation_summary",
    "created_at",
    "updated_at",
    "start_date",
    "due_date",
    "closed_at",
    "url",
    "is_open",
    "is_complete",
    "age_days",
    "days_since_update",
    "days_to_complete",
    "completed_date",
    "completed_week",
    "completed_month",
)
COMPLETE_STATUSES = {"done", "closed"}
NON_OPEN_STATUSES = {"rejected"}
IN_PROGRESS_STATUSES = {"in progress"}
BLOCKED_STATUSES = {"blocked"}


def _link(item: dict[str, Any], key: str) -> dict[str, Any]:
    return item.get("_links", {}).get(key) or {}


def _linked_id(item: dict[str, Any], key: str) -> int | None:
    href = _link(item, key).get("href")
    if not href:
        return None
    try:
        return int(str(href).rstrip("/").split("/")[-1])
    except ValueError:
        return None


def _date(value: str | None) -> date | None:
    return date.fromisoformat(value[:10]) if value else None


def _datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def normalize(
    item: dict[str, Any], base_url: str, now: datetime, timezone: str
) -> dict[str, Any]:
    work_package_id = int(item["id"])
    zone = ZoneInfo(timezone)
    today = now.astimezone(zone).date()
    created = _datetime(item.get("createdAt"))
    updated = _datetime(item.get("updatedAt"))
    closed = _datetime(item.get("closedAt"))
    completed = closed.astimezone(zone).date() if closed else None
    status = str(_link(item, "status").get("title") or "")
    normalized_status = status.casefold()
    is_complete = normalized_status in COMPLETE_STATUSES
    is_open = not is_complete and normalized_status not in NON_OPEN_STATUSES
    description = item.get("description") or {}
    if not isinstance(description, dict):
        description = {}
    return {
        "work_package_id": work_package_id,
        "project_id": _linked_id(item, "project"),
        "project": _link(item, "project").get("title"),
        "subject": item.get("subject"),
        "description": description.get("raw"),
        "type": _link(item, "type").get("title"),
        "status": status,
        "priority": _link(item, "priority").get("title"),
        "assignee": _link(item, "assignee").get("title"),
        "parent_id": _linked_id(item, "parent"),
        "version": _link(item, "version").get("title"),
        "release_id": _linked_id(item, "version"),
        "release": _link(item, "version").get("title"),
        "created_at": created,
        "updated_at": updated,
        "start_date": _date(item.get("startDate")),
        "due_date": _date(item.get("dueDate")),
        "closed_at": closed,
        "url": f"{base_url.rstrip('/')}/work_packages/{work_package_id}",
        "is_open": is_open,
        "is_complete": is_complete,
        "age_days": (today - created.astimezone(zone).date()).days if created else None,
        "days_since_update": (today - updated.astimezone(zone).date()).days
        if updated
        else None,
        "days_to_complete": (completed - created.astimezone(zone).date()).days
        if completed and created
        else None,
        "completed_date": completed,
        "completed_week": completed.strftime("%G-W%V") if completed else None,
        "completed_month": completed.strftime("%Y-%m") if completed else None,
    }


def is_story(item: dict[str, Any]) -> bool:
    return str(_link(item, "type").get("title") or "").strip().casefold() == "story"


def implementation_summary(activities: list[dict[str, Any]]) -> str | None:
    """Select the newest explicitly labelled implementation comment, not history."""
    candidates = []
    for activity in activities:
        comment = activity.get("comment") or {}
        raw = comment.get("raw") if isinstance(comment, dict) else None
        if not isinstance(raw, str) or not re.match(
            r"^\s*(?:#{1,6}\s*)?implementation (?:update|summary)\b",
            raw,
            re.IGNORECASE,
        ):
            continue
        candidates.append(activity)
    if not candidates:
        return None
    latest = max(
        candidates,
        key=lambda activity: (
            _datetime(activity.get("createdAt")) or datetime.min.replace(tzinfo=UTC),
            int(activity.get("id", 0)),
        ),
    )
    return str(latest["comment"]["raw"]).strip()


def dataset(
    items: list[dict[str, Any]],
    base_url: str,
    now: datetime,
    timezone: str,
    *,
    activities: dict[int, list[dict[str, Any]]] | None = None,
) -> list[dict[str, Any]]:
    # Keep the full hierarchy for resolution, but emit only operational Stories.
    by_id: dict[int, dict[str, Any]] = {}
    for item in items:
        key = int(item["id"])
        previous = by_id.get(key)
        if previous is None or (
            _datetime(item.get("updatedAt")) or datetime.min.replace(tzinfo=UTC)
        ) > (_datetime(previous.get("updatedAt")) or datetime.min.replace(tzinfo=UTC)):
            by_id[key] = item
    rows = []
    for key, item in sorted(by_id.items()):
        if not is_story(item):
            continue
        row = normalize(item, base_url, now, timezone)
        row.update(initiative_id=None, initiative=None, epic_id=None, epic=None)
        seen = {key}
        parent_id = row["parent_id"]
        while parent_id is not None and parent_id not in seen:
            seen.add(parent_id)
            parent = by_id.get(parent_id)
            if parent is None:
                break
            kind = str(_link(parent, "type").get("title") or "").casefold()
            if kind in {"initiative", "epic"} and row[f"{kind}_id"] is None:
                row[f"{kind}_id"] = parent_id
                row[kind] = parent.get("subject")
            parent_id = _linked_id(parent, "parent")
        row["implementation_summary"] = implementation_summary(
            (activities or {}).get(key, [])
        )
        rows.append(row)
    return rows


def projects(
    rows: list[dict[str, Any]],
    today: date,
    catalog: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    rows = [row for row in rows if str(row.get("type") or "").casefold() == "story"]
    groups: dict[tuple[int | None, str | None], list[dict[str, Any]]] = {}
    for project in catalog or []:
        groups[(int(project["id"]), str(project["name"]))] = []
    for row in rows:
        key = (row["project_id"], row["project"])
        if catalog is not None and row["project_id"] is not None:
            key = next(
                (
                    candidate
                    for candidate in groups
                    if candidate[0] == row["project_id"]
                ),
                key,
            )
        groups.setdefault(key, []).append(row)
    result = []
    for (project_id, name), items in sorted(
        groups.items(), key=lambda entry: (entry[0][0] or 0, entry[0][1] or "")
    ):
        result.append(
            {
                "project_id": project_id,
                "project": name,
                "total_work_packages": len(items),
                "open": sum(row["is_open"] for row in items),
                "in_progress": sum(
                    row["status"].casefold() in IN_PROGRESS_STATUSES for row in items
                ),
                "blocked": sum(
                    row["status"].casefold() in BLOCKED_STATUSES for row in items
                ),
                "completed": sum(row["is_complete"] for row in items),
                "completed_last_7_days": sum(
                    bool(
                        row["completed_date"]
                        and today - timedelta(days=7) < row["completed_date"] <= today
                    )
                    for row in items
                ),
                "completed_last_30_days": sum(
                    bool(
                        row["completed_date"]
                        and today - timedelta(days=30) < row["completed_date"] <= today
                    )
                    for row in items
                ),
            }
        )
    return result


def progress(rows: list[dict[str, Any]], today: date) -> list[dict[str, Any]]:
    rows = [row for row in rows if str(row.get("type") or "").casefold() == "story"]
    # Completion dates are the only available history; current open count is a snapshot.
    counts = Counter(
        row["completed_week"]
        for row in rows
        if row["is_complete"] and row["completed_week"]
    )
    cumulative = 0
    result = []
    for week in sorted(counts):
        cumulative += counts[week]
        result.append(
            {
                "completed_week": week,
                "completed": counts[week],
                "cumulative_completions": cumulative,
                "remaining_open_as_of_run": sum(row["is_open"] for row in rows),
                "snapshot_date": today,
            }
        )
    return result
