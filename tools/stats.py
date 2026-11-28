"""Draws the two stat cards of the profile README (assets/stats-*.svg, assets/streak-*.svg).

Same reasoning as tools/contributions.py: the public github-readme-stats and
streak-stats services can go down any day, so the numbers are read straight
from GitHub's GraphQL API and drawn here. The nightly workflow reruns it.

  stats   commits (last year), pull requests, issues, repositories contributed to (last year)
  streak  total contributions since the account was created, current streak, longest streak

Run by the workflow with its own token, which only sees public activity, as
the old cards did. A personal token would also count private work: the numbers
would jump from one night to the next. Standard library only.
Icons: GitHub Octicons (MIT).
"""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from pathlib import Path

from contributions import FONT, graphql

LOGIN = "Tibxla"
OUT = Path(__file__).resolve().parent.parent / "assets"

THEMES = {
    "dark": dict(label="#c9d1d9", value="#f0f6fc", muted="#8b949e", accent="#00c6ff", fire="#ff2a5c", rule="#30363d"),
    "light": dict(label="#24292f", value="#1f2328", muted="#59636e", accent="#0a8fd6", fire="#e0244f", rule="#d1d9e0"),
}

ICONS = {  # Octicons 16px
    "history": "m.427 1.927 1.215 1.215a8.002 8.002 0 1 1-1.6 5.685.75.75 0 1 1 1.493-.154 6.5 6.5 0 1 0 1.18-4.458l1.358 1.358A.25.25 0 0 1 3.896 6H.25A.25.25 0 0 1 0 5.75V2.104a.25.25 0 0 1 .427-.177ZM7.75 4a.75.75 0 0 1 .75.75v2.992l2.028.812a.75.75 0 0 1-.557 1.392l-2.5-1A.751.751 0 0 1 7 8.25v-3.5A.75.75 0 0 1 7.75 4Z",
    "pr": "M1.5 3.25a2.25 2.25 0 1 1 3 2.122v5.256a2.251 2.251 0 1 1-1.5 0V5.372A2.25 2.25 0 0 1 1.5 3.25Zm5.677-.177L9.573.677A.25.25 0 0 1 10 .854V2.5h1A2.5 2.5 0 0 1 13.5 5v5.628a2.251 2.251 0 1 1-1.5 0V5a1 1 0 0 0-1-1h-1v1.646a.25.25 0 0 1-.427.177L7.177 3.427a.25.25 0 0 1 0-.354ZM3.75 2.5a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5Zm0 9.5a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5Zm8.25.75a.75.75 0 1 0 1.5 0 .75.75 0 0 0-1.5 0Z",
    "issue": "M8 9.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Z M8 0a8 8 0 1 1 0 16A8 8 0 0 1 8 0ZM1.5 8a6.5 6.5 0 1 0 13 0 6.5 6.5 0 0 0-13 0Z",
    "repo": "M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5 9h8ZM5 12.25a.25.25 0 0 1 .25-.25h3.5a.25.25 0 0 1 .25.25v3.25a.25.25 0 0 1-.4.2l-1.45-1.087a.249.249 0 0 0-.3 0L5.4 15.7a.25.25 0 0 1-.4-.2Z",
    "flame": "M9.533.753V.752c.217 2.385 1.463 3.626 2.653 4.81C13.37 6.74 14.498 7.863 14.498 10c0 3.5-3 6-6.5 6S1.5 13.512 1.5 10c0-1.298.536-2.56 1.425-3.286.376-.308.862 0 1.035.454C4.46 8.487 5.581 8.419 6 8c.282-.282.341-.811-.003-1.5C4.34 3.187 7.035.75 8.77.146c.39-.137.726.194.763.607ZM7.998 14.5c2.832 0 5-1.98 5-4.5 0-1.463-.68-2.19-1.879-3.383l-.036-.037c-1.013-1.008-2.3-2.29-2.834-4.434-.322.256-.63.579-.864.953-.432.696-.621 1.58-.046 2.73.473.947.67 2.284-.278 3.232-.61.61-1.545.84-2.403.633a2.79 2.79 0 0 1-1.436-.874A3.198 3.198 0 0 0 3 10c0 2.53 2.164 4.5 4.998 4.5Z",
}

H = 180
MOTION = (
    ".f{animation:fade .7s ease-out both}@keyframes fade{from{opacity:0;transform:translateY(4px)}}"
    "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
)


# ---------------------------------------------------------------- data


def fetch() -> dict:
    q = """query($login:String!){user(login:$login){createdAt
      pullRequests{totalCount} issues{totalCount}
      repositoriesContributedTo(first:1,contributionTypes:[COMMIT,ISSUE,PULL_REQUEST,REPOSITORY]){totalCount}
      contributionsCollection{totalCommitContributions restrictedContributionsCount}}}"""
    u = graphql(q, {"login": LOGIN})["user"]
    created = datetime.fromisoformat(u["createdAt"].replace("Z", "+00:00")).date()

    # every calendar day since the account exists, one year per query
    days: dict[date, int] = {}
    cal_q = """query($login:String!,$from:DateTime!,$to:DateTime!){user(login:$login){
      contributionsCollection(from:$from,to:$to){contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}"""
    for year in range(created.year, date.today().year + 1):
        r = graphql(cal_q, {"login": LOGIN, "from": f"{year}-01-01T00:00:00Z", "to": f"{year}-12-31T23:59:59Z"})
        for w in r["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]:
            for d in w["contributionDays"]:
                days[date.fromisoformat(d["date"])] = d["contributionCount"]
    today = min(max(days), date.today())  # the calendar runs to Dec 31, future days at 0
    series = [(d, days.get(d, 0)) for d in (created + timedelta(n) for n in range((today - created).days + 1))]

    # current streak: today may still be empty, then it counts from yesterday
    i = len(series) - 1
    if series[i][1] == 0:
        i -= 1
    end = i
    while i >= 0 and series[i][1] > 0:
        i -= 1
    current = (end - i, series[i + 1][0] if end > i else None, series[end][0] if end > i else None)

    best, run_start = (0, None, None), None
    for k, (d, c) in enumerate(series):
        if c > 0:
            run_start = run_start if run_start is not None else k
            if k - run_start + 1 > best[0]:
                best = (k - run_start + 1, series[run_start][0], d)
        else:
            run_start = None

    cc = u["contributionsCollection"]
    return dict(
        commits=cc["totalCommitContributions"] + cc["restrictedContributionsCount"],
        prs=u["pullRequests"]["totalCount"],
        issues=u["issues"]["totalCount"],
        contributed=u["repositoriesContributedTo"]["totalCount"],
        total=sum(c for _, c in series),
        since=created,
        current=current,
        longest=best,
    )


# ---------------------------------------------------------------- drawing


def short(n: int) -> str:
    return f"{n / 1000:.1f}k".replace(".0k", "k") if n >= 1000 else str(n)


def span(a: date | None, b: date | None) -> str:
    if a is None:
        return "No streak yet"
    fmt = lambda d: d.strftime("%b ") + str(d.day)
    return fmt(a) if a == b else f"{fmt(a)} - {fmt(b)}"


def svg(w: int, body: str, label: str, css: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {H}" width="{w}" height="{H}" role="img" '
        f'aria-label="{label}"><title>{label}</title><style>{css}{MOTION}</style>{body}</svg>\n'
    )


def stats_card(s: dict, t: dict) -> str:
    rows = [
        ("history", "Total Commits (last year):", short(s["commits"])),
        ("pr", "Total PRs:", short(s["prs"])),
        ("issue", "Total Issues:", short(s["issues"])),
        ("repo", "Contributed to (last year):", short(s["contributed"])),
    ]
    css = (
        f".k{{font:600 14px {FONT};fill:{t['label']}}}"
        f".v{{font:700 14px {FONT};fill:{t['value']}}}"
    )
    out = []
    for i, (icon, k, v) in enumerate(rows):
        y = 48 + i * 30
        out.append(
            f'<g class="f" style="animation-delay:{0.15 * i:.2f}s">'
            f'<path transform="translate(25 {y - 12})" d="{ICONS[icon]}" fill="{t["accent"]}"/>'
            f'<text class="k" x="52" y="{y}">{k}</text><text class="v" x="290" y="{y}">{v}</text></g>'
        )
    label = ", ".join(f"{k} {v}" for _, k, v in rows)
    return svg(340, "".join(out), label, css)


def streak_card(s: dict, t: dict) -> str:
    W = 495
    col = W / 3
    css = (
        f".n{{font:700 28px {FONT};fill:{t['value']}}}"
        f".l{{font:400 14px {FONT};fill:{t['label']}}}"
        f".la{{font:700 14px {FONT};fill:{t['accent']}}}"
        f".d{{font:400 12px {FONT};fill:{t['muted']}}}"
    )
    cur, best = s["current"], s["longest"]
    cx = [col / 2, col * 1.5, col * 2.5]
    since = s["since"].strftime("%b ") + f"{s['since'].day}, {s['since'].year} - Present"
    out = [
        f'<line x1="{col:.1f}" y1="28" x2="{col:.1f}" y2="152" stroke="{t["rule"]}"/>',
        f'<line x1="{2 * col:.1f}" y1="28" x2="{2 * col:.1f}" y2="152" stroke="{t["rule"]}"/>',
        # total
        f'<g class="f"><text class="n" x="{cx[0]:.1f}" y="82" text-anchor="middle">{s["total"]:,}</text>'
        f'<text class="l" x="{cx[0]:.1f}" y="114" text-anchor="middle">Total Contributions</text>'
        f'<text class="d" x="{cx[0]:.1f}" y="138" text-anchor="middle">{since}</text></g>',
        # current: ring with a gap at the top for the flame
        f'<circle class="f" cx="{cx[1]:.1f}" cy="71" r="38" fill="none" stroke="{t["accent"]}" stroke-width="5" '
        f'pathLength="1" stroke-dasharray=".9 .1" transform="rotate(-72 {cx[1]:.1f} 71)"/>',
        f'<path transform="translate({cx[1] - 9:.1f} 22) scale(1.15)" d="{ICONS["flame"]}" fill="{t["fire"]}"/>',
        f'<g class="f" style="animation-delay:.3s"><text class="n" x="{cx[1]:.1f}" y="81" text-anchor="middle">{cur[0]}</text>'
        f'<text class="la" x="{cx[1]:.1f}" y="134" text-anchor="middle">Current Streak</text>'
        f'<text class="d" x="{cx[1]:.1f}" y="156" text-anchor="middle">{span(cur[1], cur[2])}</text></g>',
        # longest
        f'<g class="f" style="animation-delay:.5s"><text class="n" x="{cx[2]:.1f}" y="82" text-anchor="middle">{best[0]}</text>'
        f'<text class="l" x="{cx[2]:.1f}" y="114" text-anchor="middle">Longest Streak</text>'
        f'<text class="d" x="{cx[2]:.1f}" y="138" text-anchor="middle">{span(best[1], best[2])}</text></g>',
    ]
    label = f"{s['total']:,} contributions since {s['since'].year}, current streak {cur[0]} days, longest streak {best[0]} days"
    return svg(W, "".join(out), label, css)


def main() -> None:
    s = fetch()
    OUT.mkdir(exist_ok=True)
    for name, t in THEMES.items():
        (OUT / f"stats-{name}.svg").write_text(stats_card(s, t))
        (OUT / f"streak-{name}.svg").write_text(streak_card(s, t))
        print(f"assets/stats-{name}.svg assets/streak-{name}.svg")


if __name__ == "__main__":
    main()
