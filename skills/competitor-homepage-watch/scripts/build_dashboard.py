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
# Brand series — refined, on-system, cycled deterministically by sorted brand+country
PALETTE = ["#0f5f5c", "#1f7a5a", "#a8452f", "#7a4fa0", "#2c6b8a", "#9a6a12",
           "#556b2f", "#b0567a"]


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

    # SVG Gantt: left label column + day grid (weekend shading, month/week ticks)
    LABEL_W, DAY_W, ROW_H, PAD_T = 158, max(15, int(640 / span_days)), 30, 34
    SANS = "system-ui,-apple-system,Segoe UI,Roboto,sans-serif"
    MONO = "ui-monospace,SF Mono,Menlo,monospace"
    chart_w = LABEL_W + span_days * DAY_W + 24
    total_rows = sum(len(v) for v in rows.values())
    chart_h = PAD_T + total_rows * ROW_H + 12
    grid_top, grid_bot = PAD_T - 4, chart_h - 10
    svg = [f'<svg viewBox="0 0 {chart_w} {chart_h}" width="100%" height="{chart_h}" role="img" aria-label="Frise des opérations">']
    # weekend column shading (drawn first, behind everything)
    for i in range(span_days):
        day = win_start + datetime.timedelta(days=i)
        if day.weekday() >= 5:
            x = LABEL_W + i * DAY_W
            svg.append(f'<rect x="{x}" y="{grid_top}" width="{DAY_W}" height="{grid_bot-grid_top}" fill="#0f5f5c" opacity="0.04"/>')
    # day gridlines + day-number ticks (Mondays + the 1st)
    for i in range(span_days):
        x = LABEL_W + i * DAY_W
        day = win_start + datetime.timedelta(days=i)
        svg.append(f'<line x1="{x}" y1="{grid_top}" x2="{x}" y2="{grid_bot}" stroke="#dbe0dd" stroke-width="{1 if day.weekday()==0 else 0.5}"/>')
        if day.day == 1 or day.weekday() == 0:
            svg.append(f'<text x="{x+3}" y="{grid_top-8}" font-size="10" fill="#93a09b" font-family="{MONO}">{day.day:02d}</text>')
    y = PAD_T
    for key in sorted(rows):
        color = brand_color[key]
        for o, cs, ce in sorted(rows[key], key=lambda t: t[1]):
            x = LABEL_W + (cs - win_start).days * DAY_W
            w = max(DAY_W - 3, ((ce - cs).days + 1) * DAY_W - 3)
            ongoing_bar = o.get("status") == "ongoing"
            # brand chip + label
            svg.append(f'<rect x="0" y="{y+ROW_H//2-4}" width="8" height="8" rx="2" fill="{color}"/>')
            svg.append(f'<text x="14" y="{y+ROW_H//2+4}" font-size="11.5" fill="#5c6b67" font-family="{SANS}">{esc(o["brand"])} {esc(o["country"])}</text>')
            bar_h = ROW_H - 12
            svg.append(f'<rect x="{x}" y="{y+5}" width="{w}" height="{bar_h}" rx="5" fill="{color}"><title>{esc(o["title"])}</title></rect>')
            # soft top highlight for a bit of depth
            svg.append(f'<rect x="{x}" y="{y+5}" width="{w}" height="{bar_h/2}" rx="5" fill="#ffffff" opacity="0.10"/>')
            if ongoing_bar:  # open-ended marker: fading tail
                svg.append(f'<rect x="{x+w-6}" y="{y+5}" width="6" height="{bar_h}" fill="{color}" opacity="0.45"/>')
            cap = o["title"] if len(o["title"]) < 30 else o["title"][:27] + "…"
            disc = f"  {o['discount']}" if o.get("discount") else ""
            if w > 70:
                svg.append(f'<text x="{x+9}" y="{y+ROW_H//2+4}" font-size="10.5" fill="#ffffff" font-weight="600" font-family="{SANS}">{esc(cap)}</text>')
                if disc:
                    svg.append(f'<text x="{x+w-8}" y="{y+ROW_H//2+4}" font-size="10.5" fill="#ffffff" font-weight="700" text-anchor="end" font-family="{MONO}">{esc(o["discount"])}</text>')
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
            f'<h3><span class="chip" style="background:{brand_color[key]}"></span>{esc(key[0])} · {esc(key[1])}</h3>'
            f'<table><thead><tr><th>Opération</th><th>Remise</th><th>Début</th><th>Fin</th></tr></thead><tbody>{cells}</tbody></table>')

    css = """
:root {
  --paper:#f6f7f5; --card:#ffffff; --ink:#12211f; --petrol:#0f5f5c;
  --amber:#c8792b; --muted:#5c6b67; --faint:#93a09b; --line:#dbe0dd;
  --serif:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,"Times New Roman",serif;
  --sans:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  --mono:ui-monospace,"SF Mono","Cascadia Code",Menlo,Consolas,monospace;
}
* { box-sizing:border-box; margin:0; }
body { font-family:var(--sans); background:var(--paper); color:var(--ink);
  line-height:1.55; padding:40px 18px; -webkit-font-smoothing:antialiased; }
.wrap { max-width:940px; margin:0 auto; }
.masthead { border-top:3px solid var(--ink); padding-top:14px; margin-bottom:26px; }
.eyebrow { font-size:11px; letter-spacing:.18em; text-transform:uppercase;
  color:var(--petrol); font-weight:600; }
.masthead h1 { font-family:var(--serif); font-size:32px; line-height:1.08;
  font-weight:600; letter-spacing:-.01em; margin:6px 0 8px; text-wrap:balance; }
.masthead .meta { font-family:var(--mono); font-size:12px; color:var(--muted);
  border-top:1px solid var(--line); padding-top:8px; }
.kpis { display:grid; grid-template-columns:repeat(4,1fr); gap:1px;
  background:var(--line); border:1px solid var(--line); border-radius:12px;
  overflow:hidden; margin:0 0 30px; }
.kpi { background:var(--card); padding:16px; }
.kpi b { display:block; font-family:var(--mono); font-size:30px; font-weight:600;
  line-height:1; font-variant-numeric:tabular-nums; }
.kpi span { display:block; font-size:10.5px; letter-spacing:.08em;
  text-transform:uppercase; color:var(--muted); margin-top:7px; }
h2 { font-family:var(--sans); font-size:12px; letter-spacing:.14em;
  text-transform:uppercase; color:var(--muted); font-weight:600;
  margin:30px 0 12px; padding-bottom:7px; border-bottom:1px solid var(--line);
  display:flex; align-items:center; gap:8px; }
h2::before { content:""; width:7px; height:7px; border-radius:2px;
  background:var(--petrol); display:inline-block; }
h3 { font-family:var(--serif); font-size:16px; font-weight:600; margin:18px 0 6px;
  display:flex; align-items:center; gap:8px; }
h3 .chip { width:9px; height:9px; border-radius:3px; display:inline-block; }
.panel { background:var(--card); border:1px solid var(--line); border-radius:10px;
  padding:18px 20px; overflow-x:auto; }
table { border-collapse:collapse; width:100%; font-size:12.5px; margin-bottom:4px; }
th { text-align:left; padding:7px 8px; color:var(--faint); font-weight:600;
  font-size:10px; letter-spacing:.07em; text-transform:uppercase;
  border-bottom:1px solid var(--line); }
td { border-bottom:1px solid #eef1ee; padding:7px 8px; }
td:nth-child(2),td:nth-child(3),td:nth-child(4){ font-family:var(--mono); font-size:12px; }
tr:last-child td { border-bottom:none; }
.empty { color:var(--muted); font-size:13.5px; font-style:italic; }
footer { font-family:var(--mono); text-align:center; color:var(--faint);
  font-size:10.5px; margin-top:34px; border-top:1px solid var(--line); padding-top:14px; }
@media print { body { background:#fff; padding:0; } .panel,.kpis { border-color:#ccc; } h2 { break-after:avoid; } }
"""

    page = f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tableau de bord — {esc(title)}</title><style>{css}</style></head>
<body><div class="wrap">
<div class="masthead">
<div class="eyebrow">Veille concurrentielle · Plan commercial du marché</div>
<h1>{esc(title)}</h1>
<div class="meta">Vue cumulée · {esc(win_start.isoformat())} → {esc(win_end.isoformat())} · {len(active)} opérations</div>
</div>
<div class="kpis">
<div class="kpi"><b>{started}</b><span>Démarrées</span></div>
<div class="kpi"><b>{ended}</b><span>Terminées</span></div>
<div class="kpi"><b>{ongoing}</b><span>En cours</span></div>
<div class="kpi"><b>{len(rows)}</b><span>Enseignes actives</span></div>
</div>
<h2>Frise des opérations</h2>
<div class="panel">{gantt}</div>
<h2>Détail par enseigne</h2>
<div class="panel">{''.join(brand_rows) if brand_rows else '<p class="empty">Aucune opération.</p>'}</div>
<footer>competitor-homepage-watch · vue cumulée régénérée à la demande · dates observées lors des passages quotidiens</footer>
</div></body></html>"""

    out = ws / "dashboard.html"
    out.write_text(page, encoding="utf-8")
    print(f"dashboard written: {out} ({title}, {len(active)} operations)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
