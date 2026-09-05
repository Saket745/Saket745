#!/usr/bin/env python3
"""Detect activity, recalculate GitHub statistics, and write data/stats.json.

Deliberately split into a cheap phase and an expensive phase:

  cheap phase  -> 1 API call (public events). Runs every scheduled tick.
                  Decides whether anything is actually worth doing.
  expensive phase -> ~5-40 API calls (profile, repos, languages, multi-year
                  GraphQL contribution history). Only runs when the cheap
                  phase found new activity, a heartbeat interval elapsed, or
                  the workflow was triggered explicitly (dispatch/manual).

This is the "event-driven" contract: most ticks cost one HTTP request and
exit. Nothing is recomputed, nothing is rendered, nothing is committed
unless there's a reason to.

Privacy note: the public "recent activity" feed shown on the dashboard is
always sourced from /events/public, regardless of which token is
configured. An elevated token (see lib/github_client.py) is only ever used
to pull *aggregate numeric* contribution totals via GraphQL — the same
category of aggregate-private-contribution-count GitHub already shows on
your public contribution graph. It is never used to expose private repo
names, descriptions, or activity details on the public dashboard.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from lib.github_client import GitHubClient, resolve_token
from lib.stats import (
    aggregate_languages,
    calendar_days,
    compute_streaks,
    diff_activity,
    merge_year_calendars,
    sum_contribution_years,
    summarize_event,
)

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / ".state"
DATA_DIR = ROOT / "data"
LAST_EVENT_FILE = STATE_DIR / "last-event.json"
LIFETIME_CACHE_FILE = STATE_DIR / "lifetime-cache.json"
STATS_FILE = DATA_DIR / "stats.json"

CONTRIB_FIELDS = """
    totalCommitContributions
    totalIssueContributions
    totalPullRequestContributions
    totalPullRequestReviewContributions
    contributionCalendar { weeks { contributionDays { date contributionCount } } }
"""


def read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def emit_output(name: str, value: str) -> None:
    gh_output = os.getenv("GITHUB_OUTPUT")
    print(f"{name}={value}")
    if gh_output:
        with open(gh_output, "a", encoding="utf-8") as fh:
            fh.write(f"{name}={value}\n")


def fetch_year_contributions(client: GitHubClient, login: str, year: int) -> dict:
    query = f"""
    query($login: String!) {{
      user(login: $login) {{
        contributionsCollection(from: "{year}-01-01T00:00:00Z", to: "{year}-12-31T23:59:59Z") {{
          {CONTRIB_FIELDS}
        }}
      }}
    }}
    """
    data = client.graphql(query, {"login": login})
    return data["user"]["contributionsCollection"]


def main() -> None:
    user = os.getenv("PROFILE_USER", "Saket745")
    heartbeat_hours = float(os.getenv("HEARTBEAT_HOURS", "6"))
    force = os.getenv("FORCE_REFRESH", "0") == "1"
    trigger_event = os.getenv("GITHUB_EVENT_NAME", "manual")

    token, token_source = resolve_token()
    client = GitHubClient(token=token, source=token_source)

    # ---- cheap phase --------------------------------------------------
    public_events = client.get(f"https://api.github.com/users/{user}/events/public?per_page=30")
    last_event_state = read_json(LAST_EVENT_FILE, {})
    activity = diff_activity(public_events, last_event_state.get("latest_event_id"))

    last_full_run_at = last_event_state.get("last_full_run_at")
    heartbeat_due = True
    if last_full_run_at:
        elapsed_hours = (
            datetime.now(timezone.utc) - datetime.fromisoformat(last_full_run_at)
        ).total_seconds() / 3600
        heartbeat_due = elapsed_hours >= heartbeat_hours

    explicit_trigger = trigger_event in ("repository_dispatch", "workflow_dispatch")
    should_run_full = force or explicit_trigger or activity["has_new_activity"] or heartbeat_due or not STATS_FILE.exists()

    if not should_run_full:
        # Nothing happened, heartbeat not due, no explicit ask. Record the
        # latest event id so we don't re-evaluate the same events next
        # tick, but do NOT touch data/stats.json or render anything.
        write_json(LAST_EVENT_FILE, {**last_event_state, "latest_event_id": activity["latest_event_id"]})
        emit_output("changed", "false")
        emit_output("reason", "idle")
        print("No new activity and heartbeat not due — skipping full recalculation.")
        return

    reason = (
        "explicit-trigger" if explicit_trigger else
        "new-activity" if activity["has_new_activity"] else
        "heartbeat" if heartbeat_due and STATS_FILE.exists() else
        "first-run"
    )
    print(f"Running full recalculation (reason={reason}, token={token_source}).")

    # ---- expensive phase ------------------------------------------------
    profile = client.get(f"https://api.github.com/users/{user}")
    repos = client.get_paginated(f"https://api.github.com/users/{user}/repos?type=owner&sort=updated")
    repos = [r for r in repos if not r.get("fork") and not r.get("archived")]

    language_maps = []
    for repo in repos[:60]:  # bound the fan-out for very large accounts
        try:
            language_maps.append(client.get(repo["languages_url"]))
        except Exception:
            continue
    languages = aggregate_languages(language_maps)

    account_query = """
    query($login: String!) {
      user(login: $login) {
        createdAt
        followers { totalCount }
        following { totalCount }
      }
    }
    """
    account = client.graphql(account_query, {"login": user})["user"]
    created_year = int(account["createdAt"][:4])
    current_year = datetime.now(timezone.utc).year

    lifetime_cache = read_json(LIFETIME_CACHE_FILE, {})
    per_year_totals: dict[str, dict] = dict(lifetime_cache.get("years", {}))
    per_year_calendars: dict[str, list] = {
        year: days for year, days in lifetime_cache.get("calendars", {}).items()
    }

    for year in range(created_year, current_year):  # past, immutable years — cache-once
        key = str(year)
        if key not in per_year_totals:
            collection = fetch_year_contributions(client, user, year)
            per_year_totals[key] = {k: v for k, v in collection.items() if k != "contributionCalendar"}
            per_year_calendars[key] = calendar_days(collection["contributionCalendar"])

    current_collection = fetch_year_contributions(client, user, current_year)
    per_year_totals[str(current_year)] = {
        k: v for k, v in current_collection.items() if k != "contributionCalendar"
    }
    per_year_calendars[str(current_year)] = calendar_days(current_collection["contributionCalendar"])

    write_json(LIFETIME_CACHE_FILE, {"years": per_year_totals, "calendars": {
        # only persist calendars for years that are actually over — no point
        # re-caching the in-progress current year.
        y: d for y, d in per_year_calendars.items() if int(y) < current_year
    }})

    lifetime_totals = sum_contribution_years(per_year_totals)
    all_days = merge_year_calendars(per_year_calendars)
    streaks = compute_streaks(all_days)

    recent_activity = [summarize_event(e) for e in (activity["new_events"] or public_events)[:6]]

    stats = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "trigger": {"event": trigger_event, "reason": reason, "token_source": token_source},
        "profile": {
            "login": profile.get("login"),
            "name": profile.get("name"),
            "public_repos": profile.get("public_repos", 0),
            "followers": account["followers"]["totalCount"],
            "following": account["following"]["totalCount"],
            "account_created": account["createdAt"],
        },
        "repos": {
            "total_stars": sum(int(r.get("stargazers_count", 0)) for r in repos),
            "total_forks": sum(int(r.get("forks_count", 0)) for r in repos),
            "count": len(repos),
            "most_starred": max(repos, key=lambda r: r.get("stargazers_count", 0))["name"] if repos else None,
        },
        "languages": languages,
        "contributions": {
            "current_year": {k: v for k, v in current_collection.items() if k != "contributionCalendar"},
            "lifetime": lifetime_totals,
            "years_counted": len(per_year_totals),
        },
        "streaks": streaks,
        "recent_activity": recent_activity,
    }

    write_json(STATS_FILE, stats)
    write_json(LAST_EVENT_FILE, {
        "latest_event_id": activity["latest_event_id"],
        "last_full_run_at": stats["generated_at"],
    })
    emit_output("changed", "true")
    emit_output("reason", reason)


if __name__ == "__main__":
    main()
