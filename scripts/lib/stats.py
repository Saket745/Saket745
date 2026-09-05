"""Pure, testable computations over raw GitHub API data.

Nothing in this file makes a network call. Everything here is the
"recalculation" layer: turning raw API responses into derived metrics
GitHub doesn't hand you directly (lifetime totals across years, streaks,
language percentages, a diff against the last known activity).
"""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timezone


def short_number(value: int) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}k"
    return str(value)


def aggregate_languages(repo_language_maps: list[dict], top_n: int = 6) -> list[dict]:
    totals: Counter = Counter()
    for languages in repo_language_maps:
        for name, byte_count in (languages or {}).items():
            totals[name] += int(byte_count)
    total = sum(totals.values())
    if not total:
        return []
    return [
        {"name": name, "bytes": count, "percent": round(count * 100 / total, 1)}
        for name, count in totals.most_common(top_n)
    ]


def calendar_days(contribution_calendar: dict) -> list[dict]:
    """Flatten a GraphQL contributionCalendar into a chronological day list."""
    days = []
    for week in contribution_calendar.get("weeks", []):
        for day in week.get("contributionDays", []):
            days.append(day)
    days.sort(key=lambda d: d["date"])
    return days


def compute_streaks(all_days_chronological: list[dict], today: date | None = None) -> dict:
    """Current + longest contribution streak across the full available history.

    `all_days_chronological` should already be de-duplicated by date and
    sorted ascending (oldest first) — see merge_year_calendars below.
    """
    today = today or datetime.now(timezone.utc).date()
    longest = 0
    running = 0
    for day in all_days_chronological:
        if day["contributionCount"] > 0:
            running += 1
            longest = max(longest, running)
        else:
            running = 0

    # Current streak: walk backward from the most recent day. If the most
    # recent day on record is "today" with zero contributions yet, that
    # doesn't break an in-progress streak (the day isn't over) — skip it and
    # start counting from the day before.
    current = 0
    days_desc = list(reversed(all_days_chronological))
    if days_desc and days_desc[0]["date"] == today.isoformat() and days_desc[0]["contributionCount"] == 0:
        days_desc = days_desc[1:]
    for day in days_desc:
        if day["contributionCount"] > 0:
            current += 1
        else:
            break

    return {"current_streak": current, "longest_streak": longest}


def merge_year_calendars(calendars_by_year: dict[str, dict]) -> list[dict]:
    """Merge cached-past-year + live-current-year calendars into one
    chronological, de-duplicated day list (current year wins on overlap)."""
    by_date: dict[str, dict] = {}
    for year in sorted(calendars_by_year):
        for day in calendars_by_year[year]:
            by_date[day["date"]] = day
    return [by_date[d] for d in sorted(by_date)]


def sum_contribution_years(per_year_totals: dict[str, dict]) -> dict:
    keys = (
        "totalCommitContributions",
        "totalIssueContributions",
        "totalPullRequestContributions",
        "totalPullRequestReviewContributions",
    )
    summed = {k: 0 for k in keys}
    for year_totals in per_year_totals.values():
        for k in keys:
            summed[k] += int(year_totals.get(k, 0))
    return summed


def summarize_event(item: dict) -> dict:
    event_type = item.get("type", "Event")
    payload = item.get("payload") or {}
    action = payload.get("action")
    label = event_type.replace("Event", "")
    if label == "Push":
        commit_count = len(payload.get("commits") or [])
        label = f"Commit{'s' if commit_count != 1 else ''} pushed"
    elif label == "Watch":
        label = "Starred"
    elif label == "Create":
        ref_type = payload.get("ref_type", "")
        label = f"Created {ref_type}".strip()
    elif action:
        label = f"{label} \u2022 {action}"
    return {
        "id": item.get("id"),
        "label": label,
        "repo": (item.get("repo") or {}).get("name", ""),
        "created_at": item.get("created_at"),
    }


def diff_activity(events: list[dict], last_seen_event_id: str | None) -> dict:
    """Decide whether new activity happened since the last recorded run.

    Returns the newest event id/time (to persist) plus whether anything is
    new, so the caller can skip the expensive recompute+render+commit path
    when nothing has happened.
    """
    if not events:
        return {"has_new_activity": False, "latest_event_id": last_seen_event_id, "new_events": []}

    latest_event_id = events[0].get("id")
    if last_seen_event_id is None:
        # First run ever — treat as new so we produce an initial dashboard.
        return {"has_new_activity": True, "latest_event_id": latest_event_id, "new_events": events[:6]}

    new_events = []
    for item in events:
        if item.get("id") == last_seen_event_id:
            break
        new_events.append(item)

    return {
        "has_new_activity": bool(new_events),
        "latest_event_id": latest_event_id,
        "new_events": new_events,
    }
