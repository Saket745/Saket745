from pathlib import Path
import html
import re

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "widgets"


def inner_svg(raw: str) -> str:
    """Return the generated snake SVG's drawable content without its outer <svg>."""
    match = re.search(r"<svg[^>]*>(.*)</svg>\s*$", raw, flags=re.DOTALL | re.IGNORECASE)
    return match.group(1) if match else raw


for name in ["github-snake.svg", "github-snake-dark.svg"]:
    src = OUT / name
    if not src.exists():
        continue

    target = OUT / ("github-snake-glass-dark.svg" if "dark" in name else "github-snake-glass.svg")
    content = inner_svg(src.read_text(encoding="utf-8"))

    wrapped = f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="300" viewBox="0 0 900 300" role="img" aria-label="GITHUB STREAK • CONTRIBUTION SNAKE">
<defs>
 <linearGradient id="glass-bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#0d1727"/><stop offset=".5" stop-color="#0a1220"/><stop offset="1" stop-color="#171027"/></linearGradient>
 <linearGradient id="glass-edge" x1="0" x2="1"><stop stop-color="#48c5ff"/><stop offset=".5" stop-color="#a875ff"/><stop offset="1" stop-color="#42dfcf"/></linearGradient>
 <filter id="glass-soft"><feGaussianBlur stdDeviation="20"/></filter>
 <pattern id="glass-grid" width="24" height="24" patternUnits="userSpaceOnUse"><path d="M24 0H0V24" fill="none" stroke="#80bfff" stroke-opacity=".045"/></pattern>
</defs>
<rect x="2" y="2" width="896" height="296" rx="28" fill="url(#glass-bg)" stroke="url(#glass-edge)" stroke-width="1.4"/>
<ellipse cx="95" cy="-5" rx="220" ry="110" fill="#287eff" opacity=".10" filter="url(#glass-soft)"/>
<ellipse cx="820" cy="315" rx="230" ry="130" fill="#9b55ff" opacity=".08" filter="url(#glass-soft)"/>
<rect x="3" y="3" width="894" height="294" rx="27" fill="url(#glass-grid)"/>
<text x="34" y="39" fill="#f5f9ff" font-family="Segoe UI,Arial" font-size="20" font-weight="700" letter-spacing=".8">GITHUB STREAK • CONTRIBUTION SNAKE</text>
<text x="34" y="60" fill="#91a7ca" font-family="Segoe UI,Arial" font-size="11">Saket745 • contribution activity transformed into a neon path</text>
<rect x="28" y="78" width="844" height="194" rx="19" fill="#07111f" fill-opacity=".62" stroke="#60799e" stroke-opacity=".28"/>
<g transform="translate(45,92) scale(0.906,0.906)">
{content}
</g>
</svg>'''

    target.write_text(wrapped, encoding="utf-8")
