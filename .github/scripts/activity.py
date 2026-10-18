#!/usr/bin/env python3
import json
import os
import random
import datetime as dt
import urllib.request

LOGIN = os.environ.get("GH_LOGIN", "Zariffs")
TOKEN = os.environ.get("GH_TOKEN", "")
OUT_DIR = os.environ.get("OUT_DIR", "dist")

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays { date contributionCount contributionLevel weekday }
        }
      }
    }
  }
}
"""

LEVEL_INDEX = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}

THEMES = {
    "dark": {
        "levels": ["#1e1e1e", "#454545", "#787878", "#b0b0b0", "#f5f5f5"],
        "label": "#6e7681", "accent": "#f0f0f0", "sweep": "#ffffff", "sweep_opacity": 0.55,
    },
    "light": {
        "levels": ["#ececec", "#c4c4c4", "#909090", "#585858", "#111111"],
        "label": "#8c959f", "accent": "#111111", "sweep": "#000000", "sweep_opacity": 0.30,
    },
}

MONO = "'SF Mono', 'JetBrains Mono', Menlo, Consolas, 'Courier New', monospace"
WIDTH, HEIGHT = 1200, 250
CELL, PITCH = 17, 21.6
GRID_X, GRID_Y = 28, 52
SWEEP_SECONDS = 7


def fetch_weeks():
    body = json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json", "User-Agent": "profile-activity"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    if "errors" in data:
        raise SystemExit(f"GraphQL error: {data['errors']}")
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = [
        [(d["date"], d["contributionCount"], LEVEL_INDEX.get(d["contributionLevel"], 0), d["weekday"])
         for d in w["contributionDays"]]
        for w in cal["weeks"]
    ]
    return weeks, cal["totalContributions"]


def demo_weeks():
    today = dt.date.today()
    start = today - dt.timedelta(days=364 + (today.weekday() + 1) % 7)
    weeks, week, total = [], [], 0
    d = start
    while d <= today:
        lvl = random.choices([0, 1, 2, 3, 4], [60, 15, 12, 8, 5])[0]
        week.append((d.isoformat(), lvl * 2, lvl, (d.weekday() + 1) % 7))
        total += lvl * 2
        if len(week) == 7:
            weeks.append(week)
            week = []
        d += dt.timedelta(days=1)
    if week:
        weeks.append(week)
    return weeks, total


def month_labels(weeks):
    labels, last = [], None
    for i, week in enumerate(weeks):
        first = dt.date.fromisoformat(week[0][0])
        if first.month != last and first.day <= 7:
            labels.append((i, first.strftime("%b").upper()))
            last = first.month
    return labels


def render(weeks, total, theme):
    t = THEMES[theme]
    weeks = weeks[-53:]
    cells, mask = [], []
    for col, week in enumerate(weeks):
        for date, count, lvl, weekday in week:
            x, y = GRID_X + col * PITCH, GRID_Y + weekday * PITCH
            cells.append(
                f'<rect class="c" x="{x:.1f}" y="{y:.1f}" width="{CELL}" height="{CELL}" rx="3.5" '
                f'fill="{t["levels"][lvl]}" style="animation-delay:{round(col * 0.012, 3)}s">'
                f"<title>{date}: {count} contribution{'s' if count != 1 else ''}</title></rect>"
            )
            mask.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{CELL}" height="{CELL}" rx="3.5" fill="#fff"/>')
    months = "".join(f'<text x="{GRID_X + c * PITCH:.1f}" y="{GRID_Y - 14}">{n}</text>' for c, n in month_labels(weeks))
    legend_y = GRID_Y + 7 * PITCH + 22
    legend = "".join(
        f'<rect x="{1172 - (5 - i) * 21.6 + 4.6:.1f}" y="{legend_y - 12}" width="13" height="13" rx="3" fill="{c}"/>'
        for i, c in enumerate(t["levels"])
    )
    updated = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" width="{WIDTH}" height="{HEIGHT}">
  <defs>
    <linearGradient id="sweepFill" x1="0" x2="1" y1="0" y2="0">
      <stop offset="0" stop-color="{t['sweep']}" stop-opacity="0"/>
      <stop offset="0.5" stop-color="{t['sweep']}" stop-opacity="{t['sweep_opacity']}"/>
      <stop offset="1" stop-color="{t['sweep']}" stop-opacity="0"/>
    </linearGradient>
    <mask id="cells" maskUnits="userSpaceOnUse" x="0" y="0" width="{WIDTH}" height="{HEIGHT}">{''.join(mask)}</mask>
  </defs>
  <style>
    @keyframes rise {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
    .c {{ animation: rise 0.6s ease-out both; }}
  </style>
  <g font-family="{MONO}" font-size="11" fill="{t['label']}" letter-spacing="2">{months}</g>
  <g>{''.join(cells)}</g>
  <g mask="url(#cells)">
    <rect x="-360" y="0" width="300" height="{HEIGHT}" fill="url(#sweepFill)">
      <animate attributeName="x" from="-360" to="{WIDTH + 60}" dur="{SWEEP_SECONDS}s"
               repeatCount="indefinite" calcMode="spline" keyTimes="0;1" keySplines="0.45 0 0.55 1"/>
    </rect>
  </g>
  <g font-family="{MONO}" font-size="12" letter-spacing="2">
    <text x="{GRID_X}" y="{legend_y}" fill="{t['accent']}">{total} CONTRIBUTIONS · LAST 12 MONTHS</text>
    <text x="{1172 - 5 * 21.6 - 12:.1f}" y="{legend_y}" fill="{t['label']}" text-anchor="end">LESS</text>
    <text x="1172" y="{legend_y + 22}" fill="{t['label']}" text-anchor="end" font-size="10">UPDATED {updated}</text>
  </g>
  {legend}
</svg>
"""


def main():
    weeks, total = demo_weeks() if os.environ.get("DEMO") else fetch_weeks()
    os.makedirs(OUT_DIR, exist_ok=True)
    for theme in THEMES:
        path = os.path.join(OUT_DIR, f"activity-{theme}.svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write(render(weeks, total, theme))


if __name__ == "__main__":
    main()
