#!/usr/bin/env python3
"""render_report.py — [mutating] Render the daily events into a self-contained HTML report.

Builds <workspace>/reports/<date>.html from events/<date>.json, diffs/<date>.json
(when present) and calendar/calendar.json. The page is designed for non-technical
readers: KPI header, per-brand activity chart (inline SVG), one card per event
with the evidence quote and the screenshot when available. No external assets —
it opens offline with a double click and prints cleanly to PDF from the browser.

Exit codes: 0 = report written, 1 = bad usage/missing events file.
Python 3.8+, standard library only.
"""

import argparse
import html
import json
import sys
from collections import Counter
from pathlib import Path

TYPE_META = {
    "promo_start": ("Nouvelle opération", "#0e7a4a", "#e6f5ee"),
    "promo_end": ("Opération terminée", "#a33b3b", "#faecec"),
    "promo_update": ("Opération modifiée", "#8a6d1a", "#faf4e0"),
    "other_change": ("Changement notable", "#41586e", "#eef2f6"),
}

CSS = """
* { box-sizing: border-box; margin: 0; }
body { font-family: "Helvetica Neue", Arial, sans-serif; background: #f2f4f7; color: #1f2733;
       line-height: 1.5; padding: 28px 16px; }
.wrap { max-width: 860px; margin: 0 auto; }
header { background: #0f2a43; color: #fff; border-radius: 10px; padding: 22px 26px; }
header h1 { font-size: 21px; font-weight: 600; }
header p { color: #b9c8d8; font-size: 13px; margin-top: 4px; }
.kpis { display: flex; gap: 12px; margin: 16px 0 22px; flex-wrap: wrap; }
.kpi { flex: 1 1 120px; background: #fff; border-radius: 10px; padding: 14px 16px;
       border: 1px solid #e3e8ee; }
.kpi b { display: block; font-size: 26px; font-variant-numeric: tabular-nums; }
.kpi span { font-size: 12px; color: #5b6b7c; }
h2 { font-size: 15px; color: #0f2a43; margin: 24px 0 10px; }
.card { background: #fff; border: 1px solid #e3e8ee; border-radius: 10px;
        padding: 16px 18px; margin-bottom: 12px; page-break-inside: avoid; }
.tag { display: inline-block; font-size: 11px; font-weight: 600; padding: 3px 9px;
       border-radius: 99px; margin-bottom: 8px; }
.card h3 { font-size: 15px; margin-bottom: 4px; }
.card .brand { font-size: 12px; color: #5b6b7c; margin-bottom: 8px; }
.card .disc { font-weight: 700; color: #0e7a4a; }
blockquote { border-left: 3px solid #c9d2dc; padding: 6px 12px; margin: 10px 0;
             color: #44546a; font-size: 13px; background: #f7f9fb; }
.card img { max-width: 100%; border: 1px solid #e3e8ee; border-radius: 6px; margin-top: 10px; }
.chart { background: #fff; border: 1px solid #e3e8ee; border-radius: 10px; padding: 16px 18px; }
.issues { background: #fff8e6; border: 1px solid #e8d9a0; border-radius: 10px;
          padding: 12px 16px; font-size: 13px; color: #6b5a1a; }
.empty { color: #5b6b7c; font-size: 13px; padding: 8px 2px; }
footer { text-align: center; color: #8b98a7; font-size: 11px; margin-top: 26px; }
@media print { body { background: #fff; padding: 0; } .card, .chart { border-color: #ccc; } }
"""


def esc(s):
    return html.escape(str(s or ""))


def event_card(ev, workspace, reports_dir):
    label, color, bg = TYPE_META.get(ev.get("event_type"), TYPE_META["other_change"])
    disc = f' <span class="disc">{esc(ev["discount"])}</span>' if ev.get("discount") else ""
    end = (ev.get("dates_seen") or {}).get("announced_end")
    end_html = f'<div class="brand">Fin annoncée : {esc(end)}</div>' if end else ""
    quote = f"<blockquote>« {esc(ev['evidence'])} »</blockquote>" if ev.get("evidence") else ""
    img = ""
    shot = ev.get("screenshot")
    if shot:
        shot_abs = (workspace / shot).resolve()
        if shot_abs.exists():
            try:
                rel = shot_abs.relative_to(reports_dir.parent)
                img = f'<img src="../{rel.as_posix()}" alt="capture">'
            except ValueError:
                img = f'<img src="{shot_abs.as_uri()}" alt="capture">'
    return f"""<div class="card">
<span class="tag" style="color:{color};background:{bg}">{label}</span>
<h3>{esc(ev.get('title', '(sans titre)'))}{disc}</h3>
<div class="brand">{esc(ev['brand'])} — {esc(ev['country'])}</div>
{end_html}<p style="font-size:13px">{esc(ev.get('summary', ''))}</p>
{quote}{img}
</div>"""


def brand_chart(calendar):
    counts = Counter()
    for op in calendar.get("operations", []):
        if op.get("type") == "operation" and op.get("status") == "ongoing":
            counts[f"{op['brand']} {op['country']}"] += 1
    if not counts:
        return '<p class="empty">Aucune opération en cours dans le calendrier.</p>'
    top = counts.most_common(10)
    peak = max(c for _, c in top)
    rows, y = [], 0
    for name, c in top:
        w = int(480 * c / peak)
        rows.append(
            f'<text x="0" y="{y+14}" font-size="12" fill="#44546a">{esc(name)}</text>'
            f'<rect x="170" y="{y+3}" width="{w}" height="14" rx="3" fill="#1d4e79"></rect>'
            f'<text x="{176+w}" y="{y+14}" font-size="12" fill="#0f2a43" font-weight="600">{c}</text>'
        )
        y += 26
    return (f'<svg viewBox="0 0 700 {y}" width="100%" height="{y}" role="img" '
            f'aria-label="Opérations en cours par enseigne">{"".join(rows)}</svg>')


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--date", default=None, help="events date YYYY-MM-DD (default: latest events file)")
    args = ap.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    events_dir = workspace / "events"
    if args.date:
        events_path = events_dir / f"{args.date}.json"
    else:
        candidates = sorted(events_dir.glob("*.json")) if events_dir.is_dir() else []
        events_path = candidates[-1] if candidates else None
    if not events_path or not events_path.exists():
        print(f"ERROR: no events file found ({events_path or events_dir})", file=sys.stderr)
        return 1
    date = events_path.stem
    events = json.loads(events_path.read_text(encoding="utf-8"))

    calendar_path = workspace / "calendar" / "calendar.json"
    calendar = json.loads(calendar_path.read_text(encoding="utf-8")) if calendar_path.exists() else {"operations": []}
    diff_path = workspace / "diffs" / f"{date}.json"
    diff = json.loads(diff_path.read_text(encoding="utf-8")) if diff_path.exists() else None

    by_type = {k: [e for e in events if e.get("event_type") == k] for k in TYPE_META}
    ongoing = sum(1 for op in calendar["operations"]
                  if op.get("type") == "operation" and op.get("status") == "ongoing")

    reports_dir = workspace / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    issues = []
    if diff:
        for t in diff.get("targets", []):
            if t.get("status") == "fetch_failed":
                issues.append(f"{t['slug']} : capture en échec ({esc(t.get('error', ''))})")
    baseline = f" · Comparé au {esc(diff['baseline'])}" if diff else ""

    sections = []
    for key, title in [("promo_start", "🆕 Nouvelles opérations"),
                       ("promo_end", "🔚 Opérations terminées"),
                       ("promo_update", "✏️ Opérations modifiées"),
                       ("other_change", "📋 Autres changements")]:
        if by_type[key]:
            cards = "".join(event_card(e, workspace, reports_dir) for e in by_type[key])
            sections.append(f"<h2>{title}</h2>{cards}")
    if not sections:
        sections.append('<h2>Résultat</h2><p class="empty">Aucun changement commercial détecté aujourd\'hui.</p>')
    issues_html = ""
    if issues:
        issues_html = '<h2>⚠️ Problèmes de surveillance</h2><div class="issues">' + "<br>".join(issues) + "</div>"

    page = f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Veille concurrentielle — {esc(date)}</title><style>{CSS}</style></head>
<body><div class="wrap">
<header><h1>Veille concurrentielle — {esc(date)}</h1>
<p>Rapport quotidien{baseline}</p></header>
<div class="kpis">
<div class="kpi"><b>{len(by_type['promo_start'])}</b><span>nouvelles opérations</span></div>
<div class="kpi"><b>{len(by_type['promo_end'])}</b><span>opérations terminées</span></div>
<div class="kpi"><b>{len(by_type['promo_update'])}</b><span>modifications</span></div>
<div class="kpi"><b>{ongoing}</b><span>opérations en cours (marché)</span></div>
</div>
{''.join(sections)}
{issues_html}
<h2>📊 Opérations en cours par enseigne</h2>
<div class="chart">{brand_chart(calendar)}</div>
<footer>Généré par competitor-homepage-watch · Les dates sont des dates observées lors des passages quotidiens.</footer>
</div></body></html>"""

    out = reports_dir / f"{date}.html"
    out.write_text(page, encoding="utf-8")
    print(f"report written: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
