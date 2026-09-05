#!/usr/bin/env python3
"""Render assets/widgets/profile-dashboard.svg from data/stats.json.

Pure function of the data file — no network calls here. Keeping rendering
separate from collection means the glass theme can be redesigned without
touching a single GitHub API call, and the JSON snapshot stays inspectable
on its own (it's a small, genuinely useful "stats API" in the repo).
"""
from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path

from lib.stats import short_number

ROOT = Path(__file__).resolve().parents[1]
STATS_FILE = ROOT / "data" / "stats.json"
OUT = ROOT / "assets" / "widgets" / "profile-dashboard.svg"
STACK_FILE = ROOT / "profile-stack.json"

W, H = 1100, 920
ACCENT = ["#48c5ff", "#9a6dff", "#42dfcf", "#ffc15b", "#ff6fae", "#77a7ff"]
FONT = "Segoe UI,Arial"


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def truncate(text: str, limit: int) -> str:
    text = str(text)
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "\u2026"


def glass_panel(x, y, w, h, r=22) -> str:
    """A glass panel: translucent fill, soft border, and a thin inner
    highlight along the top edge to fake a light catching the glass."""
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" '
        f'fill="#0c1728" fill-opacity=".88" stroke="#5574a5" stroke-opacity=".38"/>'
        f'<path d="M{x+r} {y+1.4} H{x+w-r}" stroke="#dff1ff" stroke-opacity=".16" '
        f'stroke-width="1.1" stroke-linecap="round"/>'
    )


def defs_block() -> str:
    return "".join([
        "<defs>",
        '<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
        '<stop stop-color="#08111f"/><stop offset=".48" stop-color="#0b1424"/>'
        '<stop offset="1" stop-color="#1a1028"/></linearGradient>',
        '<linearGradient id="edge" x1="0" x2="1"><stop stop-color="#48c5ff"/>'
        '<stop offset=".5" stop-color="#a875ff"/><stop offset="1" stop-color="#42dfcf"/></linearGradient>',
        '<linearGradient id="glowLine" x1="0" x2="1"><stop stop-color="#48c5ff"/>'
        '<stop offset=".5" stop-color="#9a6dff"/><stop offset="1" stop-color="#42dfcf"/></linearGradient>',
        '<filter id="blur"><feGaussianBlur stdDeviation="30"/></filter>',
        '<filter id="glow"><feGaussianBlur stdDeviation="4" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>',
        '<pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse">'
        '<path d="M24 0H0V24" fill="none" stroke="#80bfff" stroke-opacity=".04"/></pattern>',
        # subtle grain so the glass reads as textured rather than flat-blurred
        '<filter id="grain"><feTurbulence type="fractalNoise" baseFrequency="0.9" '
        'numOctaves="2" stitchTiles="stitch" result="n"/>'
        '<feColorMatrix in="n" type="matrix" values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 0.02 0"/></filter>',
        "</defs>",
    ])


def stat_card(x, y, w, h, title, value, sub, accent, pulse=False) -> str:
    dot = (
        f'<circle cx="{x+w-18}" cy="{y+20}" r="4" fill="{accent}" filter="url(#glow)">'
        + ('<animate attributeName="opacity" values="1;.45;1" dur="2.4s" repeatCount="indefinite"/>' if pulse else '')
        + '</circle>'
    )
    return (
        glass_panel(x, y, w, h, 20)
        + dot
        + f'<text x="{x+20}" y="{y+27}" fill="#8fa6c9" font-family="{FONT}" font-size="10.5" '
          f'font-weight="700" letter-spacing="1.1">{esc(title)}</text>'
        + f'<text x="{x+20}" y="{y+h-27}" fill="#f4f8ff" font-family="{FONT}" font-size="28" '
          f'font-weight="800">{esc(value)}</text>'
        + f'<text x="{x+w-20}" y="{y+h-29}" fill="#6f86a8" font-family="{FONT}" font-size="10" '
          f'text-anchor="end">{esc(sub)}</text>'
    )


def panel_header(x, y, title, subtitle) -> str:
    return (
        f'<text x="{x+22}" y="{y+34}" fill="#f5f8ff" font-family="{FONT}" font-size="20" '
        f'font-weight="750">{esc(title)}</text>'
        f'<text x="{x+22}" y="{y+55}" fill="#8fa6c9" font-family="{FONT}" font-size="11">{esc(subtitle)}</text>'
    )


def build_svg(stats: dict, stack: list[tuple[str, str]]) -> str:
    profile = stats["profile"]
    repos = stats["repos"]
    languages = stats["languages"]
    lifetime = stats["contributions"]["lifetime"]
    years_counted = stats["contributions"]["years_counted"]
    streaks = stats["streaks"]
    activity = stats["recent_activity"]
    trigger = stats.get("trigger", {})

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'role="img" aria-label="{esc(profile.get("login", "GitHub"))} profile intelligence dashboard">',
        defs_block(),
        f'<rect x="2" y="2" width="{W-4}" height="{H-4}" rx="34" fill="url(#bg)" stroke="url(#edge)" stroke-width="1.6"/>',
        '<ellipse cx="120" cy="0" rx="320" ry="180" fill="#257dff" opacity=".10" filter="url(#blur)"/>',
        f'<ellipse cx="{W-80}" cy="{H-60}" rx="340" ry="200" fill="#a052ff" opacity=".09" filter="url(#blur)"/>',
        f'<rect x="3" y="3" width="{W-6}" height="{H-6}" rx="33" fill="url(#grid)"/>',
        f'<rect x="3" y="3" width="{W-6}" height="{H-6}" rx="33" filter="url(#grain)" opacity=".5"/>',
        f'<text x="48" y="58" fill="#f7faff" font-family="{FONT}" font-size="30" font-weight="800" '
        f'letter-spacing="1.5">{esc(profile.get("login", "").upper())} \u2022 GITHUB TELEMETRY</text>',
        f'<text x="48" y="84" fill="#8fa6c9" font-family="{FONT}" font-size="13">'
        f'{esc(profile.get("name") or profile.get("login", ""))} \u00b7 event-driven profile intelligence \u00b7 '
        f'no server, no hosting \u2014 pure GitHub Actions</text>',
        '<g transform="translate(858,36)"><circle cx="10" cy="10" r="7" fill="#42dfcf" filter="url(#glow)">'
        '<animate attributeName="opacity" values="1;.5;1" dur="2.2s" repeatCount="indefinite"/></circle>'
        f'<text x="25" y="15" fill="#9cefe4" font-family="{FONT}" font-size="12" font-weight="700">EVENT-DRIVEN</text></g>',
    ]

    # 3x2 stat grid
    stat_defs = [
        ("REPOSITORIES", profile.get("public_repos", 0), "public, non-fork", ACCENT[0], False),
        ("FOLLOWERS", profile.get("followers", 0), "community", ACCENT[1], False),
        ("FOLLOWING", profile.get("following", 0), "network", ACCENT[2], False),
        ("TOTAL STARS", repos.get("total_stars", 0), "across repos", ACCENT[3], False),
        ("TOTAL FORKS", repos.get("total_forks", 0), "across repos", ACCENT[4], False),
        ("CURRENT STREAK", f'{streaks.get("current_streak", 0)}d', "consecutive days", ACCENT[5], True),
    ]
    for i, (title, value, sub, accent, pulse) in enumerate(stat_defs):
        col, row = i % 3, i // 3
        x = 48 + col * 336
        y = 116 + row * 112
        parts.append(stat_card(x, y, 312, 92, title, short_number(value) if isinstance(value, int) else value, sub, accent, pulse))

    # top languages
    x, y, w, h = 48, 350, 500, 250
    parts.append(glass_panel(x, y, w, h, 24))
    parts.append(panel_header(x, y, "TOP LANGUAGES", "Repository composition \u00b7 recalculated from language bytes"))
    ly = y + 84
    for i, lang in enumerate(languages):
        c = ACCENT[i % len(ACCENT)]
        barw = 260 * lang["percent"] / 100
        parts.append(f'<circle cx="{x+28}" cy="{ly}" r="5" fill="{c}" filter="url(#glow)"/>')
        parts.append(f'<text x="{x+42}" y="{ly+4}" fill="#eaf1fd" font-family="{FONT}" font-size="12.5" font-weight="650">{esc(lang["name"])}</text>')
        parts.append(f'<rect x="{x+160}" y="{ly-5}" width="260" height="9" rx="4.5" fill="#15243a"/>')
        parts.append(f'<rect x="{x+160}" y="{ly-5}" width="{barw:.1f}" height="9" rx="4.5" fill="url(#glowLine)"/>')
        parts.append(f'<text x="{x+468}" y="{ly+4}" fill="#c8d6ec" font-family="{FONT}" font-size="11" text-anchor="end">{lang["percent"]:.1f}%</text>')
        ly += 31
    if not languages:
        parts.append(f'<text x="{x+28}" y="{ly}" fill="#7189ad" font-family="{FONT}" font-size="12">No language data yet.</text>')

    # live activity
    x, y, w, h = 570, 350, 482, 250
    parts.append(glass_panel(x, y, w, h, 24))
    parts.append(panel_header(x, y, "RECENT ACTIVITY", "New public GitHub events detected since the last refresh"))
    ay = y + 82
    for i, item in enumerate(activity):
        c = ACCENT[i % len(ACCENT)]
        parts.append(f'<circle cx="{x+26}" cy="{ay-2}" r="4" fill="{c}" filter="url(#glow)"/>')
        parts.append(f'<text x="{x+40}" y="{ay+2}" fill="#eaf1fd" font-family="{FONT}" font-size="11.5" font-weight="650">{esc(item["label"])[:38]}</text>')
        parts.append(f'<text x="{x+40}" y="{ay+18}" fill="#7189ad" font-family="{FONT}" font-size="9.8">{esc(item["repo"])[:50]}</text>')
        ay += 29
    if not activity:
        parts.append(f'<text x="{x+26}" y="{ay}" fill="#7189ad" font-family="{FONT}" font-size="12">No new public events yet.</text>')

    # lifetime contributions (recalculated across every year of the account)
    x, y, w, h = 48, 624, 500, 240
    parts.append(glass_panel(x, y, w, h, 24))
    parts.append(panel_header(x, y, "LIFETIME CONTRIBUTIONS", f"Recalculated across {years_counted} year(s) of account history"))
    grid_items = [
        ("COMMITS", lifetime.get("totalCommitContributions", 0)),
        ("PULL REQUESTS", lifetime.get("totalPullRequestContributions", 0)),
        ("ISSUES", lifetime.get("totalIssueContributions", 0)),
        ("REVIEWS", lifetime.get("totalPullRequestReviewContributions", 0)),
        ("LONGEST STREAK", f'{streaks.get("longest_streak", 0)}d'),
        ("MOST STARRED", truncate(repos.get("most_starred") or "\u2014", 15)),
    ]
    for i, (label, value) in enumerate(grid_items):
        col, row = i % 2, i // 2
        cx = x + 22 + col * 235
        cy = y + 96 + row * 48
        display = short_number(value) if isinstance(value, int) else str(value)
        font_size = "15" if label == "MOST STARRED" else "21"
        parts.append(f'<text x="{cx}" y="{cy}" fill="#7088aa" font-family="{FONT}" font-size="9.5" font-weight="700" letter-spacing=".8">{esc(label)}</text>')
        parts.append(f'<text x="{cx}" y="{cy+23}" fill="#f2f7ff" font-family="{FONT}" font-size="{font_size}" font-weight="800">{esc(display)}</text>')

    # tech stack
    x, y, w, h = 570, 624, 482, 240
    parts.append(glass_panel(x, y, w, h, 24))
    parts.append(panel_header(x, y, "TECH STACK", "Configured from profile-stack.json"))
    positions = [(x+20, y+78), (x+254, y+78), (x+20, y+132), (x+254, y+132), (x+20, y+186), (x+254, y+186)]
    for i, ((name, label), (tx, ty)) in enumerate(zip(stack, positions)):
        c = ACCENT[i % len(ACCENT)]
        parts.append(f'<rect x="{tx}" y="{ty}" width="205" height="40" rx="13" fill="#111f32" stroke="{c}" stroke-opacity=".24"/>')
        parts.append(f'<circle cx="{tx+14}" cy="{ty+20}" r="4" fill="{c}" filter="url(#glow)"/>')
        parts.append(f'<text x="{tx+26}" y="{ty+17}" fill="#edf4ff" font-family="{FONT}" font-size="10.5" font-weight="700">{esc(name)[:22]}</text>')
        parts.append(f'<text x="{tx+26}" y="{ty+30}" fill="#7088aa" font-family="{FONT}" font-size="8.2">{esc(label)[:28]}</text>')

    now = datetime.fromisoformat(stats["generated_at"]).strftime("%Y-%m-%d %H:%M UTC")
    reason = trigger.get("reason", "scheduled")
    parts.extend([
        f'<text x="{W-48}" y="{H-40}" fill="#627ca2" font-family="{FONT}" font-size="9.5" text-anchor="end">'
        f'SYNCED {esc(now)} \u00b7 TRIGGER {esc(reason).upper()} \u00b7 SOURCE GITHUB</text>',
        "</svg>",
    ])
    return "".join(parts)


def main() -> None:
    stats = json.loads(STATS_FILE.read_text(encoding="utf-8"))
    try:
        stack = [(x["name"], x.get("label", "")) for x in json.loads(STACK_FILE.read_text(encoding="utf-8"))][:8]
    except Exception:
        stack = [("Python", "AI / Automation"), ("C++", "DSA / Systems"), ("React", "Frontend"),
                 ("FastAPI", "Backend"), ("PyTorch", "Deep Learning"), ("OpenCV", "Computer Vision")]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build_svg(stats, stack), encoding="utf-8")
    print(f"Rendered {OUT}")


if __name__ == "__main__":
    main()
