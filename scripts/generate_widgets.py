#!/usr/bin/env python3
from __future__ import annotations
import json, os, pathlib
from collections import Counter
from urllib.request import Request, urlopen

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "widgets"
USER = os.environ.get("PROFILE_USER", "Saket745")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
STACK_FILE = ROOT / "profile-stack.json"

DEFAULT_STACK = [
    ("Python", "AI / Automation"), ("C++", "DSA / Systems"),
    ("React", "Frontend"), ("FastAPI", "Backend"),
    ("PyTorch", "Deep Learning"), ("OpenCV", "Computer Vision"),
    ("Git", "Version Control"), ("GitHub Actions", "Automation")
]


def api(url: str):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Saket745-glass-profile",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    with urlopen(Request(url, headers=headers), timeout=25) as r:
        return json.load(r)


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def frame(title: str, subtitle: str, body: str, width=630, height=350) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{esc(title)}">
<defs>
 <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#0d1727"/><stop offset=".5" stop-color="#0a1220"/><stop offset="1" stop-color="#171027"/></linearGradient>
 <linearGradient id="edge" x1="0" x2="1"><stop stop-color="#55c7ff"/><stop offset=".52" stop-color="#a875ff"/><stop offset="1" stop-color="#43e4d2"/></linearGradient>
 <linearGradient id="accent" x1="0" x2="1"><stop stop-color="#48c5ff"/><stop offset=".48" stop-color="#9a6dff"/><stop offset="1" stop-color="#42dfcf"/></linearGradient>
 <filter id="glow"><feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
 <filter id="soft"><feGaussianBlur stdDeviation="20"/></filter>
 <pattern id="grid" width="22" height="22" patternUnits="userSpaceOnUse"><path d="M22 0H0V22" fill="none" stroke="#80bfff" stroke-opacity=".045"/></pattern>
</defs>
<rect x="2" y="2" width="626" height="346" rx="28" fill="url(#bg)" stroke="url(#edge)" stroke-width="1.4"/>
<ellipse cx="95" cy="-10" rx="220" ry="110" fill="#287eff" opacity=".10" filter="url(#soft)"/>
<ellipse cx="560" cy="360" rx="230" ry="150" fill="#9b55ff" opacity=".08" filter="url(#soft)"/>
<rect x="3" y="3" width="624" height="344" rx="27" fill="url(#grid)"/>
<text x="32" y="40" fill="#f5f9ff" font-family="Segoe UI,Arial" font-size="21" font-weight="700" letter-spacing=".8">{esc(title)}</text>
<text x="32" y="61" fill="#91a7ca" font-family="Segoe UI,Arial" font-size="11.5">{esc(subtitle)}</text>
{body}
</svg>'''


def make_languages():
    counts = Counter()
    try:
        repos = api(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner&sort=updated")
        for repo in repos:
            if repo.get("fork"):
                continue
            try:
                for lang, value in api(repo["languages_url"]).items():
                    counts[lang] += int(value)
            except Exception:
                pass
    except Exception:
        repos = []

    total = sum(counts.values())
    rows = [(k, v * 100 / total) for k, v in counts.most_common(6)] if total else []
    accents = ["#48c5ff", "#a875ff", "#42dfcf", "#ffc15b", "#ff6fae", "#77a7ff"]
    body = []

    if not rows:
        body.append('<rect x="42" y="95" width="546" height="190" rx="22" fill="#0d1a2c" fill-opacity=".62" stroke="#60799e" stroke-opacity=".25"/>')
        body.append('<text x="315" y="190" text-anchor="middle" fill="#9db3d6" font-family="Segoe UI,Arial" font-size="14">SYNCING WITH GITHUB…</text>')
    else:
        y = 102
        for i, (lang, pct) in enumerate(rows):
            accent = accents[i % len(accents)]
            bar = 320 * pct / 100
            body.append(f'''<g transform="translate(34,{y})">
 <circle cx="8" cy="3" r="5.5" fill="{accent}" filter="url(#glow)"/>
 <text x="24" y="8" fill="#eef5ff" font-family="Segoe UI,Arial" font-size="13.5" font-weight="600">{esc(lang)}</text>
 <rect x="154" y="-6" width="320" height="9" rx="4.5" fill="#16243a" stroke="#5c78a4" stroke-opacity=".22"/>
 <rect x="154" y="-6" width="{bar:.1f}" height="9" rx="4.5" fill="url(#accent)" opacity=".92"/>
 <text x="518" y="8" text-anchor="end" fill="#cfddf2" font-family="Segoe UI,Arial" font-size="12.5">{pct:.1f}%</text></g>''')
            y += 38
        body.append(f'<text x="596" y="326" text-anchor="end" fill="#6680a8" font-family="Segoe UI,Arial" font-size="10.5">{esc(USER)} • live repository language composition</text>')

    (OUT / "top-languages.svg").write_text(frame("TOP LANGUAGES", "A glassmorphism view of the code you build with", "".join(body)), encoding="utf-8")


def make_stack():
    stack = DEFAULT_STACK
    try:
        stack = [(x["name"], x.get("label", "")) for x in json.loads(STACK_FILE.read_text(encoding="utf-8"))][:8]
    except Exception:
        pass
    positions = [(34,88),(190,88),(346,88),(502,88),(34,184),(190,184),(346,184),(502,184)]
    accents = ["#48c5ff","#ffc15b","#9b70ff","#42dfcf","#77a7ff","#ff7e7e","#6ee7b7","#b785ff"]
    cards=[]
    for i, ((name,label),(x,y)) in enumerate(zip(stack, positions)):
        accent = accents[i % len(accents)]
        glyph = esc("".join(c for c in name if c.isalnum())[:2].upper() or "AI")
        cards.append(f'''<g transform="translate({x},{y})">
 <rect width="132" height="78" rx="18" fill="#101c2f" fill-opacity=".84" stroke="#5d7ca9" stroke-opacity=".34"/>
 <circle cx="25" cy="26" r="13" fill="{accent}" fill-opacity=".14" stroke="{accent}" stroke-opacity=".70" filter="url(#glow)"/>
 <text x="25" y="30" text-anchor="middle" fill="{accent}" font-family="Segoe UI,Arial" font-size="8.5" font-weight="800">{glyph}</text>
 <text x="47" y="30" fill="#f2f7ff" font-family="Segoe UI,Arial" font-size="11.3" font-weight="700">{esc(name)}</text>
 <text x="16" y="58" fill="#90a6c8" font-family="Segoe UI,Arial" font-size="8.7">{esc(label)}</text></g>''')
    body = "".join(cards) + f'<text x="596" y="326" text-anchor="end" fill="#6680a8" font-family="Segoe UI,Arial" font-size="10.5">{esc(USER)} • edit profile-stack.json to personalize</text>'
    (OUT / "tech-stack.svg").write_text(frame("TECH STACK", "A modular glass panel for your builder toolkit", body), encoding="utf-8")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    make_languages()
    make_stack()
    print(f"Generated glass widgets for {USER}")
