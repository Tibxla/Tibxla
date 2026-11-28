"""Draws the contribution graph of the profile README (assets/contributions-*.svg).

The public github-readme-activity-graph service went down (HTTP 402), so the
graph is built here from GitHub's own contribution calendar and committed to
the repo. A scheduled workflow (.github/workflows/contributions.yml) reruns it
every night; nothing third-party is left between GitHub and the image.

Standard library only. Needs a token in GITHUB_TOKEN (the workflow's own token
is enough; locally: GITHUB_TOKEN=$(gh auth token) python3 tools/contributions.py).
"""

from __future__ import annotations

import json
import math
import os
import urllib.request
from datetime import date
from pathlib import Path

LOGIN = "Tibxla"
DAYS = 31
OUT = Path(__file__).resolve().parent.parent / "assets"

THEMES = {
    "dark": dict(text="#9198a1", title="#f0f6fc", grid="#ffffff14", line="#00c6ff", point="#f0f6fc"),
    "light": dict(text="#59636e", title="#1f2328", grid="#0000000f", line="#0a8fd6", point="#1f2328"),
}

W, H = 900, 300
LEFT, RIGHT, TOP, BOTTOM = 62, 24, 58, 50
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"


def graphql(query: str, variables: dict) -> dict:
    """POST a query to GitHub's GraphQL API with the token in GITHUB_TOKEN."""
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}", "User-Agent": LOGIN},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if "errors" in payload:
        raise SystemExit(f"GraphQL: {payload['errors']}")
    return payload["data"]


def fetch() -> list[tuple[date, int]]:
    query = """query($login:String!){user(login:$login){contributionsCollection{
      contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}"""
    weeks = graphql(query, {"login": LOGIN})["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    days = [(date.fromisoformat(d["date"]), d["contributionCount"]) for w in weeks for d in w["contributionDays"]]
    days.sort()
    return days[-DAYS:]


def nice_axis(v: int) -> tuple[int, int]:
    """Top of the y axis and number of intervals: the smallest readable step
    (1, 2, 2.5 or 5 times a power of ten) that covers v in at most 6 intervals."""
    v = max(v, 1)
    k = 0
    while True:
        for m in (1, 2, 2.5, 5):
            step = m * 10 ** k
            n = math.ceil(v / step)
            if n <= 6:
                return int(step * max(n, 2)), max(n, 2)
        k += 1


def monotone(pts: list[tuple[float, float]]) -> str:
    """Smooth path through the points that never overshoots (Fritsch-Carlson)."""
    n = len(pts)
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    d = [(ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]) for i in range(n - 1)]
    m = [d[0]] + [0.0 if d[i - 1] * d[i] <= 0 else (d[i - 1] + d[i]) / 2 for i in range(1, n - 1)] + [d[-1]]
    for i in range(n - 1):
        if d[i] == 0:
            m[i] = m[i + 1] = 0.0
        else:
            a, b = m[i] / d[i], m[i + 1] / d[i]
            s = a * a + b * b
            if s > 9:
                t = 3 / math.sqrt(s)
                m[i], m[i + 1] = t * a * d[i], t * b * d[i]
    out = [f"M{xs[0]:.1f} {ys[0]:.1f}"]
    for i in range(n - 1):
        h = (xs[i + 1] - xs[i]) / 3
        out.append(
            f"C{xs[i] + h:.1f} {ys[i] + m[i] * h:.1f} {xs[i + 1] - h:.1f} {ys[i + 1] - m[i + 1] * h:.1f} "
            f"{xs[i + 1]:.1f} {ys[i + 1]:.1f}"
        )
    return " ".join(out)


def graph(days: list[tuple[date, int]], t: dict) -> str:
    top, steps = nice_axis(max(c for _, c in days))
    pw, ph = W - LEFT - RIGHT, H - TOP - BOTTOM
    x = lambda i: LEFT + pw * i / (len(days) - 1)
    y = lambda v: TOP + ph * (1 - v / top)
    pts = [(x(i), y(c)) for i, (_, c) in enumerate(days)]
    line = monotone(pts)
    area = f"{line} L{pts[-1][0]:.1f} {y(0):.1f} L{pts[0][0]:.1f} {y(0):.1f} Z"
    total = sum(c for _, c in days)

    parts = []
    for k in range(steps + 1):  # horizontal grid + y labels
        v = top * k / steps
        yy = y(v)
        parts.append(f'<line x1="{LEFT}" y1="{yy:.1f}" x2="{W - RIGHT}" y2="{yy:.1f}" stroke="{t["grid"]}"/>')
        parts.append(f'<text x="{LEFT - 10}" y="{yy + 4:.1f}" text-anchor="end">{v:g}</text>')
    for i, (d, _) in enumerate(days):  # day labels
        parts.append(f'<text x="{x(i):.1f}" y="{H - BOTTOM + 20}" text-anchor="middle">{d.day}</text>')
    dots = "".join(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3"/>' for px, py in pts)
    label = f"{total:,} in the last {DAYS} days"
    css = (
        f"text{{font:11px {FONT};fill:{t['text']}}}"
        f".t{{font:600 15px {FONT};fill:{t['title']}}}"
        ".ln{stroke-dasharray:1;animation:draw 1.6s cubic-bezier(.16,1,.3,1) both}"
        "@keyframes draw{from{stroke-dashoffset:1}}"
        ".ar,.pt{animation:fade .8s .9s both}@keyframes fade{from{opacity:0}}"
        "@media (prefers-reduced-motion:reduce){.ln,.ar,.pt{animation:none}}"
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
        f'aria-label="Contributions: {label}"><title>Contributions: {label}</title><style>{css}</style>'
        f'<defs><linearGradient id="a" x1="0" x2="0" y1="0" y2="1">'
        f'<stop offset="0" stop-color="{t["line"]}" stop-opacity=".35"/>'
        f'<stop offset="1" stop-color="{t["line"]}" stop-opacity="0"/></linearGradient></defs>'
        f'<text class="t" x="{LEFT}" y="28">Contributions</text>'
        f'<text x="{W - RIGHT}" y="28" text-anchor="end">{label}</text>'
        + "".join(parts)
        + f'<path class="ar" d="{area}" fill="url(#a)"/>'
        f'<path class="ln" d="{line}" pathLength="1" fill="none" stroke="{t["line"]}" stroke-width="2.5" '
        f'stroke-linejoin="round" stroke-linecap="round"/>'
        f'<g class="pt" fill="{t["point"]}">{dots}</g>'
        "</svg>\n"
    )


def main() -> None:
    days = fetch()
    OUT.mkdir(exist_ok=True)
    for name, t in THEMES.items():
        (OUT / f"contributions-{name}.svg").write_text(graph(days, t))
        print(f"assets/contributions-{name}.svg")


if __name__ == "__main__":
    main()
