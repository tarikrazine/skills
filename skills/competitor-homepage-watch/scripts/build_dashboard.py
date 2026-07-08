#!/usr/bin/env python3
"""build_dashboard.py — [mutating] Cumulative monthly dashboard of the commercial plan.

Unlike the daily report (which shows only what changed vs the previous day), the
dashboard is a rolling, cumulative view: every operation active during a time
window drawn as a Gantt timeline, plus KPIs and a per-brand breakdown. It is the
"commercial plan of the market" at a glance, regenerated on demand.

Window: a calendar month with --month YYYY-MM (default: the current-ish latest
month present in the calendar), or a rolling N-day window with --days N.

Reads <workspace>/calendar/calendar.json, writes <workspace>/dashboard.html
(self-contained, opens with a double click, prints cleanly to PDF).

Exit codes: 0 = dashboard written, 1 = bad usage/empty calendar.
Python 3.8+, standard library only.
"""

import argparse
import datetime
import html
import json
import sys
from collections import defaultdict
from pathlib import Path

MONTHS_FR = ["", "janvier", "février", "mars", "avril", "mai", "juin", "juillet",
             "août", "septembre", "octobre", "novembre", "décembre"]
PALETTE = ["#1d4e79", "#0e7a4a", "#a3521a", "#7a3fb8", "#0f7d8a", "#b03b5a",
           "#5a6b1a", "#8a6d1a"]


def esc(s):
    return html.escape(str(s or ""))


def d(s):
    y, m, day = (int(x) for x in s.split("-"))
    return datetime.date(y, m, day)


def op_end(op):
    return op.get("ended_on") or op.get("announced_end") or op.get("last_seen")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--workspace", required=True)
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--month", default=None, help="window = this calendar month (YYYY-MM)")
    group.add_argument("--days", type=int, default=None, help="window = last N days up to the latest activity")
    args = ap.parse_args()

    ws = Path(args.workspace).expanduser().resolve()
    cal_path = ws / "calendar" / "calendar.json"
    if not cal_path.exists():
        print(f"ERROR: no calendar at {cal_path}", file=sys.stderr)
        return 1
    calendar = json.loads(cal_path.read_text(encoding="utf-8"))
    ops = [o for o in calendar.get("operations", []) if o.get("type") == "operation"]
    if not ops:
        print("ERROR: no operations in the calendar yet", file=sys.stderr)
        return 1

    # Determine window [win_start, win_end] inclusive
    latest = max(op_end(o) for o in ops)
    if args.days:
        win_end = d(latest)
        win_start = win_end - datetime.timedelta(days=args.days - 1)
        title = f"{args.days} derniers jours"
    else:
        month = args.month or latest[:7]
        y, m = int(month[:4]), int(month[5:7])
        win_start = datetime.date(y, m, 1)
        win_end = datetime.date(y + (m == 12), (m % 12) + 1, 1) - datetime.timedelta(days=1)
        title = f"{MONTHS_FR[m]} {y}"
    span_days = (win_end - win_start).days + 1

    # Operations overlapping the window
    active = []
    for o in ops:
        s, e = d(o["first_seen"]), d(op_end(o))
        if e >= win_start and s <= win_end:
            active.append((o, max(s, win_start), min(e, win_end)))

    # KPI counts within window
    started = sum(1 for o in ops if win_start <= d(o["first_seen"]) <= win_end)
    ended = sum(1 for o in ops if o.get("ended_on") and win_start <= d(o["ended_on"]) <= win_end)
    ongoing = sum(1 for o, _, _ in active if o.get("status") == "ongoing")

    # Gantt rows grouped by brand+country
    rows = defaultdict(list)
    for o, cs, ce in active:
        rows[(o["brand"], o["country"])].append((o, cs, ce))
    brand_color = {}
    for i, key in enumerate(sorted(rows)):
        brand_color[key] = PALETTE[i % len(PALETTE)]

    # SVG Gantt: left label column + day grid
    LABEL_W, DAY_W, ROW_H, PAD_T = 150, max(14, int(620 / span_days)), 26, 28
    chart_w = LABEL_W + span_days * DAY_W + 20
    total_rows = sum(len(v) for v in rows.values())
    chart_h = PAD_T + total_rows * ROW_H + 10
    svg = [f'<svg viewBox="0 0 {chart_w} {chart_h}" width="100%" height="{chart_h}" font-family="Arial" role="img" aria-label="Frise des opérations">']
    # day gridlines + weekly labels
    for i in range(span_days):
        x = LABEL_W + i * DAY_W
        day = win_start + datetime.timedelta(days=i)
        stroke = "#dde3ea" if day.weekday() < 5 else "#eef2f6"
        svg.append(f'<line x1="{x}" y1="{PAD_T}" x2="{x}" y2="{chart_h-8}" stroke="{stroke}"/>')
        if day.day == 1 or day.weekday() == 0:
            svg.append(f'<text x="{x+2}" y="{PAD_T-8}" font-size="10" fill="#8b98a7">{day.day:02d}</text>')
    y = PAD_T
    for key in sorted(rows):
        color = brand_color[key]
        for o, cs, ce in sorted(rows[key], key=lambda t: t[1]):
            x = LABEL_W + (cs - win_start).days * DAY_W
            w = max(DAY_W - 2, ((ce - cs).days + 1) * DAY_W - 2)
            label = f"{o['brand']} {o['country']}"
            svg.append(f'<text x="0" y="{y+ROW_H//2+4}" font-size="11" fill="#44546a">{esc(label)}</text>')
            svg.append(f'<rect x="{x}" y="{y+4}" width="{w}" height="{ROW_H-10}" rx="4" fill="{color}" opacity="0.92"><title>{esc(o["title"])}</title></rect>')
            cap = o["title"] if len(o["title"]) < 34 else o["title"][:31] + "…"
            disc = f" {o['discount']}" if o.get("discount") else ""
            svg.append(f'<text x="{x+6}" y="{y+ROW_H//2+4}" font-size="10.5" fill="#fff" font-weight="600">{esc(cap)}{esc(disc)}</text>')
            y += ROW_H
    svg.append("</svg>")
    gantt = "".join(svg) if active else '<p class="empty">Aucune opération dans cette fenêtre.</p>'

    # Per-brand breakdown table
    brand_rows = []
    for key in sorted(rows):
        items = sorted(rows[key], key=lambda t: t[1])
        cells = "".join(
            f'<tr><td>{esc(o["title"])}</td><td>{esc(o.get("discount") or "—")}</td>'
            f'<td>{esc(o["first_seen"])}</td>'
            f'<td>{esc(o.get("ended_on") or ("→ " + o.get("announced_end")) if o.get("announced_end") and not o.get("ended_on") else (o.get("ended_on") or "en cours"))}</td></tr>'
            for o, _, _ in items)
        brand_rows.append(
            f'<h3 style="color:{brand_color[key]}">{esc(key[0])} — {esc(key[1])}</h3>'
            f'<table><thead><tr><th>Opération</th><th>Remise</th><th>Début</th><th>Fin</th></tr></thead><tbody>{cells}</tbody></table>')

    css = """
* { box-sizing: border-box; margin: 0; }
body { font-family: "Helvetica Neue", Arial, sans-serif; background: #f2f4f7; color: #1f2733;
       line-height: 1.5; padding: 28px 16px; }
.wrap { max-width: 940px; margin: 0 auto; }
header { background: #0f2a43; color: #fff; border-radius: 10px; padding: 22px 26px; }
header h1 { font-size: 20px; font-weight: 600; }
header p { color: #b9c8d8; font-size: 13px; margin-top: 4px; }
.kpis { display: flex; gap: 12px; margin: 16px 0 22px; flex-wrap: wrap; }
.kpi { flex: 1 1 130px; background: #fff; border-radius: 10px; padding: 14px 16px; border: 1px solid #e3e8ee; }
.kpi b { display: block; font-size: 26px; font-variant-numeric: tabular-nums; }
.kpi span { font-size: 12px; color: #5b6b7c; }
h2 { font-size: 15px; color: #0f2a43; margin: 24px 0 10px; }
h3 { font-size: 13px; margin: 16px 0 6px; }
.panel { background: #fff; border: 1px solid #e3e8ee; border-radius: 10px; padding: 16px 18px; overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-size: 12.5px; margin-bottom: 6px; }
th { background: #eef2f6; text-align: left; padding: 5px 8px; color: #44546a; }
td { border-bottom: 0.5px solid #e3e8ee; padding: 5px 8px; }
.empty { color: #5b6b7c; font-size: 13px; }
footer { text-align: center; color: #8b98a7; font-size: 11px; margin-top: 26px; }
@media print { body { background: #fff; padding: 0; } }
"""

    page = f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tableau de bord — {esc(title)}</title><style>{css}</style></head>
<body><div class="wrap">
<header><h1>Plan commercial du marché — {esc(title)}</h1>
<p>Vue cumulée · {esc(win_start.isoformat())} → {esc(win_end.isoformat())} · {len(active)} opérations sur la période</p></header>
<div class="kpis">
<div class="kpi"><b>{started}</b><span>opérations démarrées</span></div>
<div class="kpi"><b>{ended}</b><span>opérations terminées</span></div>
<div class="kpi"><b>{ongoing}</b><span>encore en cours</span></div>
<div class="kpi"><b>{len(rows)}</b><span>enseignes actives</span></div>
</div>
<h2>📆 Frise des opérations</h2>
<div class="panel">{gantt}</div>
<h2>📋 Détail par enseigne</h2>
<div class="panel">{''.join(brand_rows) if brand_rows else '<p class="empty">Aucune opération.</p>'}</div>
<footer>Généré par competitor-homepage-watch · Vue cumulée régénérée à la demande · dates observées lors des passages quotidiens.</footer>
</div></body></html>"""

    out = ws / "dashboard.html"
    out.write_text(page, encoding="utf-8")
    print(f"dashboard written: {out} ({title}, {len(active)} operations)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
