#!/usr/bin/env python3
import datetime as dt
import html
import json
import os
import subprocess
from pathlib import Path

LOGIN = os.environ.get("GITHUB_USERNAME", "Sukhraj-Singh-2006")
OUTPUT = Path("assets/contribution-activity.svg")
WIDTH = 1200
HEIGHT = 430
LEFT = 85
TOP = 75
CHART_W = 1070
CHART_H = 279
MAX_VALUE = 18
DAYS = 31

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""


def fetch_contributions():
    today = dt.datetime.now(dt.timezone.utc).date()
    start = today - dt.timedelta(days=DAYS - 1)
    variables = {
        "login": LOGIN,
        "from": f"{start.isoformat()}T00:00:00Z",
        "to": f"{today.isoformat()}T23:59:59Z",
    }

    env = os.environ.copy()
    env["GH_TOKEN"] = os.environ["GH_TOKEN"]

    result = subprocess.run(
        [
            "gh", "api", "graphql",
            "-f", f"query={QUERY}",
            "-f", f"login={variables['login']}",
            "-f", f"from={variables['from']}",
            "-f", f"to={variables['to']}",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    payload = json.loads(result.stdout)
    if payload.get("errors"):
        raise RuntimeError(json.dumps(payload["errors"]))

    user = payload.get("data", {}).get("user")
    if not user:
        raise RuntimeError(f"GitHub user not found: {LOGIN}")

    values = {}
    for week in user["contributionsCollection"]["contributionCalendar"]["weeks"]:
        for day in week["contributionDays"]:
            values[day["date"]] = int(day["contributionCount"])

    return [(start + dt.timedelta(days=i), values.get((start + dt.timedelta(days=i)).isoformat(), 0)) for i in range(DAYS)]


def esc(value):
    return html.escape(str(value), quote=True)


def y_pos(value):
    # Keep the requested fixed 0-18 axis. Values above 18 are pinned at the top.
    value = min(max(value, 0), MAX_VALUE)
    return TOP + CHART_H - (value / MAX_VALUE) * CHART_H


def build_svg(data):
    x0 = LEFT
    y0 = TOP
    points = []
    for i, (date, count) in enumerate(data):
        x = x0 + (CHART_W * i / (len(data) - 1))
        y = y_pos(count)
        points.append((x, y, date, count))

    polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y, _, _ in points)
    area = f"{x0:.1f},{y0 + CHART_H:.1f} " + polyline + f" {x0 + CHART_W:.1f},{y0 + CHART_H:.1f}"

    svg = [
        f'<svg width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" xmlns="http://www.w3.org/2000/svg">',
        '<rect width="100%" height="100%" fill="#0d1117"/>',
        '<text x="600" y="45" text-anchor="middle" fill="#58a6ff" font-family="Arial, sans-serif" font-size="22" font-weight="700">'
        "Sukhraj Singh's Contribution Graph</text>",
        '<g stroke="#1f3b63" stroke-width="1" stroke-dasharray="3 3">',
    ]

    for value in range(0, MAX_VALUE + 1, 2):
        y = y_pos(value)
        svg.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x0 + CHART_W}" y2="{y:.1f}"/>')

    for i in range(len(data)):
        x = x0 + (CHART_W * i / (len(data) - 1))
        svg.append(f'<line x1="{x:.1f}" y1="{y0}" x2="{x:.1f}" y2="{y0 + CHART_H}"/>')
    svg.append('</g>')

    svg.append('<g fill="#58a6ff" font-family="Arial, sans-serif" font-size="13" text-anchor="end">')
    for value in range(MAX_VALUE, -1, -2):
        y = y_pos(value) + 5
        svg.append(f'<text x="{x0 - 12}" y="{y:.1f}">{value}</text>')
    svg.append('</g>')

    svg.append(f'<polygon points="{area}" fill="#3fb950" opacity="0.12"/>')
    svg.append(f'<polyline points="{polyline}" fill="none" stroke="#3fb950" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>')

    svg.append('<g fill="#ffffff">')
    for x, y, date, count in points:
        label = f"{date.isoformat()}: {count} contribution{'s' if count != 1 else ''}"
        svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5"><title>{esc(label)}</title></circle>')
    svg.append('</g>')

    svg.append('<g fill="#58a6ff" font-family="Arial, sans-serif" font-size="12" text-anchor="middle">')
    for x, _, date, _ in points:
        svg.append(f'<text x="{x:.1f}" y="{y0 + CHART_H + 21}">{date.day}</text>')
    svg.append('</g>')

    svg.extend([
        f'<text x="{x0 - 55}" y="{y0 + CHART_H / 2:.1f}" transform="rotate(-90 {x0 - 55} {y0 + CHART_H / 2:.1f})" text-anchor="middle" fill="#58a6ff" font-family="Arial, sans-serif" font-size="14" font-weight="600">Contributions</text>',
        f'<text x="{x0 + CHART_W / 2:.1f}" y="{y0 + CHART_H + 51}" text-anchor="middle" fill="#58a6ff" font-family="Arial, sans-serif" font-size="14" font-weight="600">Days</text>',
        '</svg>',
    ])
    return "\n".join(svg) + "\n"


def main():
    data = fetch_contributions()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(build_svg(data), encoding="utf-8")
    print(f"Updated {OUTPUT} with {len(data)} days of contribution data.")


if __name__ == "__main__":
    main()
