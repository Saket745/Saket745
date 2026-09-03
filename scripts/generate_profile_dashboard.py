#!/usr/bin/env python3
"""Generate the inline glass dashboard shown in the Saket745 profile README."""
from __future__ import annotations

import html
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "widgets" / "profile-dashboard.svg"
USER = os.getenv("PROFILE_USER", "Saket745")
TOKEN = os.getenv("GITHUB_TOKEN", "")


def api(url: str):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Saket745-profile-dashboard",
        "X-GitHub-Api-Version": "2026-03-10",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    with urlopen(Request(url, headers=headers), timeout=30) as response:
        return json.load(response)


def graphql(query: str, variables: dict):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Saket745-profile-dashboard",
        "X-GitHub-Api-Version": "2026-03-10",
        "Content-Type": "application/json",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = Request(
        "https://api.github.com/graphql",
        headers=headers,
        data=json.dumps({"query": query, "variables": variables}).encode(),
        method="POST",
    )
    with urlopen(req, timeout=30) as response:
        body = json.load(response)
    if body.get("errors"):
        raise RuntimeError("; ".join(e.get("message", "GraphQL error") for e in body["errors"]))
    return body["data"]


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def short_number(value: int) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}k"
    return str(value)


def rounded_rect(x, y, w, h, r=20, fill="#0c1728", stroke="#5574a5", opacity=".88"):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" fill-opacity="{opacity}" stroke="{stroke}" stroke-opacity=".38"/>'


def main() -> None:
    profile = api(f"https://api.github.com/users/{USER}")
    repos = api(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner&sort=updated")
    repos = [r for r in repos if not r.get("fork")]

    language_totals = Counter()
    for repo in repos:
        try:
            for lang, amount in api(repo["languages_url"]).items():
                language_totals[lang] += int(amount)
        except Exception:
            continue
    language_total = sum(language_totals.values())
    languages = [
        (name, amount * 100 / language_total)
        for name, amount in language_totals.most_common(6)
    ] if language_total else []

    query = """
    query($login:String!){
      user(login:$login){
        followers { totalCount }
        following { totalCount }
        contributionsCollection {
          totalCommitContributions
          totalIssueContributions
          totalPullRequestContributions
          totalPullRequestReviewContributions
          contributionCalendar { totalContributions }
        }
      }
    }
    """
    gql = graphql(query, {"login": USER})["user"]
    contrib = gql["contributionsCollection"]

    stars = sum(int(r.get("stargazers_count", 0)) for r in repos)
    forks = sum(int(r.get("forks_count", 0)) for r in repos)
    recent = api(f"https://api.github.com/users/{USER}/events/public?per_page=12")

    events = []
    for item in recent:
        event_type = item.get("type", "Event")
        repo_name = item.get("repo", {}).get("name", "")
        payload = item.get("payload") or {}
        action = payload.get("action")
        label = event_type.replace("Event", "")
        if action:
            label += f" • {action}"
        if label == "Push":
            commits = payload.get("commits") or []
            label = f"Commit{'s' if len(commits) != 1 else ''} pushed"
        events.append((label, repo_name))
    events = events[:6]

    stack = [
        ("Python", "AI / Automation"),
        ("C++", "DSA / Systems"),
        ("React", "Frontend"),
        ("FastAPI", "Backend"),
        ("PyTorch", "Deep Learning"),
        ("OpenCV", "Computer Vision"),
        ("Git", "Version Control"),
        ("GitHub Actions", "Automation"),
    ]
    try:
        configured = json.loads((ROOT / "profile-stack.json").read_text(encoding="utf-8"))
        stack = [(x["name"], x.get("label", "")) for x in configured][:8]
    except Exception:
        pass

    accent = ["#48c5ff", "#9a6dff", "#42dfcf", "#ffc15b", "#ff6fae", "#77a7ff"]
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="880" viewBox="0 0 1100 880" role="img" aria-label="Saket745 live GitHub glass dashboard">',
        '<defs>',
        '<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#08111f"/><stop offset=".48" stop-color="#0b1424"/><stop offset="1" stop-color="#1a1028"/></linearGradient>',
        '<linearGradient id="edge" x1="0" x2="1"><stop stop-color="#48c5ff"/><stop offset=".5" stop-color="#a875ff"/><stop offset="1" stop-color="#42dfcf"/></linearGradient>',
        '<linearGradient id="glowLine" x1="0" x2="1"><stop stop-color="#48c5ff"/><stop offset=".5" stop-color="#9a6dff"/><stop offset="1" stop-color="#42dfcf"/></linearGradient>',
        '<filter id="blur"><feGaussianBlur stdDeviation="28"/></filter>',
        '<filter id="glow"><feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>',
        '<pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse"><path d="M24 0H0V24" fill="none" stroke="#80bfff" stroke-opacity=".04"/></pattern>',
        '</defs>',
        '<rect x="2" y="2" width="1096" height="876" rx="34" fill="url(#bg)" stroke="url(#edge)" stroke-width="1.6"/>',
        '<ellipse cx="120" cy="0" rx="320" ry="180" fill="#257dff" opacity=".10" filter="url(#blur)"/>',
        '<ellipse cx="1020" cy="860" rx="340" ry="200" fill="#a052ff" opacity=".09" filter="url(#blur)"/>',
        '<rect x="3" y="3" width="1094" height="874" rx="33" fill="url(#grid)"/>',
        '<text x="48" y="58" fill="#f7faff" font-family="Segoe UI,Arial" font-size="30" font-weight="800" letter-spacing="1.5">SAKET745 • GITHUB TELEMETRY</text>',
        '<text x="48" y="84" fill="#8fa6c9" font-family="Segoe UI,Arial" font-size="13">Saket Maurya · live profile intelligence · event-driven refresh</text>',
        '<g transform="translate(890,36)"><circle cx="10" cy="10" r="7" fill="#42dfcf" filter="url(#glow)"/><text x="25" y="15" fill="#9cefe4" font-family="Segoe UI,Arial" font-size="12" font-weight="700">LIVE</text></g>',
    ]

    # Stat cards
    stats = [
        ("REPOSITORIES", profile.get("public_repos", 0), "public"),
        ("FOLLOWERS", gql["followers"]["totalCount"], "community"),
        ("FOLLOWING", gql["following"]["totalCount"], "network"),
        ("TOTAL STARS", stars, "across repos"),
        ("TOTAL FORKS", forks, "across repos"),
        ("CONTRIBUTIONS", contrib["contributionCalendar"]["totalContributions"], "current period"),
    ]
    for i, (title, value, sub) in enumerate(stats):
        col = i % 3
        row = i // 3
        x = 48 + col * 336
        y = 116 + row * 112
        parts.append(rounded_rect(x, y, 312, 92, 20))
        parts.append(f'<text x="{x+20}" y="{y+27}" fill="#8fa6c9" font-family="Segoe UI,Arial" font-size="10.5" font-weight="700" letter-spacing="1.1">{esc(title)}</text>')
        parts.append(f'<text x="{x+20}" y="{y+65}" fill="#f4f8ff" font-family="Segoe UI,Arial" font-size="28" font-weight="800">{esc(short_number(int(value)))}</text>')
        parts.append(f'<text x="{x+200}" y="{y+63}" fill="#6f86a8" font-family="Segoe UI,Arial" font-size="10" text-anchor="end">{esc(sub)}</text>')

    # Languages panel
    x, y, w, h = 48, 350, 500, 250
    parts.append(rounded_rect(x, y, w, h, 24))
    parts.append(f'<text x="{x+22}" y="{y+34}" fill="#f5f8ff" font-family="Segoe UI,Arial" font-size="20" font-weight="750">TOP LANGUAGES</text>')
    parts.append(f'<text x="{x+22}" y="{y+55}" fill="#8fa6c9" font-family="Segoe UI,Arial" font-size="11">Repository composition · calculated from language bytes</text>')
    ly = y + 84
    for i, (name, pct) in enumerate(languages):
        c = accent[i % len(accent)]
        barw = 260 * pct / 100
        parts.append(f'<circle cx="{x+28}" cy="{ly}" r="5" fill="{c}" filter="url(#glow)"/>')
        parts.append(f'<text x="{x+42}" y="{ly+4}" fill="#eaf1fd" font-family="Segoe UI,Arial" font-size="12.5" font-weight="650">{esc(name)}</text>')
        parts.append(f'<rect x="{x+160}" y="{ly-5}" width="260" height="9" rx="4.5" fill="#15243a"/>')
        parts.append(f'<rect x="{x+160}" y="{ly-5}" width="{barw:.1f}" height="9" rx="4.5" fill="url(#glowLine)"/>')
        parts.append(f'<text x="{x+468}" y="{ly+4}" fill="#c8d6ec" font-family="Segoe UI,Arial" font-size="11" text-anchor="end">{pct:.1f}%</text>')
        ly += 31

    # Activity panel
    x, y, w, h = 570, 350, 482, 250
    parts.append(rounded_rect(x, y, w, h, 24))
    parts.append(f'<text x="{x+22}" y="{y+34}" fill="#f5f8ff" font-family="Segoe UI,Arial" font-size="20" font-weight="750">LIVE ACTIVITY</text>')
    parts.append(f'<text x="{x+22}" y="{y+55}" fill="#8fa6c9" font-family="Segoe UI,Arial" font-size="11">Recent public GitHub events detected for Saket745</text>')
    ay = y + 82
    for i, (label, repo_name) in enumerate(events):
        c = accent[i % len(accent)]
        parts.append(f'<circle cx="{x+26}" cy="{ay-2}" r="4" fill="{c}" filter="url(#glow)"/>')
        parts.append(f'<text x="{x+40}" y="{ay+2}" fill="#eaf1fd" font-family="Segoe UI,Arial" font-size="11.5" font-weight="650">{esc(label)[:38]}</text>')
        parts.append(f'<text x="{x+40}" y="{ay+18}" fill="#7189ad" font-family="Segoe UI,Arial" font-size="9.8">{esc(repo_name)[:50]}</text>')
        ay += 29

    # Contributions and stack
    x, y, w, h = 48, 624, 500, 212
    parts.append(rounded_rect(x, y, w, h, 24))
    parts.append(f'<text x="{x+22}" y="{y+34}" fill="#f5f8ff" font-family="Segoe UI,Arial" font-size="20" font-weight="750">CONTRIBUTION MATRIX</text>')
    parts.append(f'<text x="{x+22}" y="{y+55}" fill="#8fa6c9" font-family="Segoe UI,Arial" font-size="11">Commits · PRs · Issues · Reviews</text>')
    contribution_items = [
        ("COMMITS", contrib["totalCommitContributions"]),
        ("PULL REQUESTS", contrib["totalPullRequestContributions"]),
        ("ISSUES", contrib["totalIssueContributions"]),
        ("REVIEWS", contrib["totalPullRequestReviewContributions"]),
    ]
    for i, (label, value) in enumerate(contribution_items):
        col = i % 2
        row = i // 2
        cx = x + 22 + col * 235
        cy = y + 96 + row * 55
        parts.append(f'<text x="{cx}" y="{cy}" fill="#7088aa" font-family="Segoe UI,Arial" font-size="9.5" font-weight="700" letter-spacing=".8">{esc(label)}</text>')
        parts.append(f'<text x="{cx}" y="{cy+25}" fill="#f2f7ff" font-family="Segoe UI,Arial" font-size="24" font-weight="800">{esc(short_number(int(value)))}</text>')

    x, y, w, h = 570, 624, 482, 212
    parts.append(rounded_rect(x, y, w, h, 24))
    parts.append(f'<text x="{x+22}" y="{y+34}" fill="#f5f8ff" font-family="Segoe UI,Arial" font-size="20" font-weight="750">TECH STACK</text>')
    parts.append(f'<text x="{x+22}" y="{y+55}" fill="#8fa6c9" font-family="Segoe UI,Arial" font-size="11">Configured from profile-stack.json</text>')
    positions = [(x+20, y+78), (x+254, y+78), (x+20, y+132), (x+254, y+132), (x+20, y+186), (x+254, y+186)]
    for i, ((name, label), (tx, ty)) in enumerate(zip(stack, positions)):
        c = accent[i % len(accent)]
        parts.append(f'<rect x="{tx}" y="{ty}" width="205" height="40" rx="13" fill="#111f32" stroke="{c}" stroke-opacity=".24"/>')
        parts.append(f'<circle cx="{tx+14}" cy="{ty+20}" r="4" fill="{c}" filter="url(#glow)"/>')
        parts.append(f'<text x="{tx+26}" y="{ty+17}" fill="#edf4ff" font-family="Segoe UI,Arial" font-size="10.5" font-weight="700">{esc(name)[:22]}</text>')
        parts.append(f'<text x="{tx+26}" y="{ty+30}" fill="#7088aa" font-family="Segoe UI,Arial" font-size="8.2">{esc(label)[:28]}</text>')

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    parts.extend([
        f'<text x="1052" y="860" fill="#627ca2" font-family="Segoe UI,Arial" font-size="9.5" text-anchor="end">SYNCED {esc(now)} · SOURCE GITHUB</text>',
        '</svg>',
    ])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(parts), encoding="utf-8")
    print(f"Generated {OUT}")


if __name__ == "__main__":
    main()
