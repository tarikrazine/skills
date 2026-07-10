#!/usr/bin/env python3
"""render_report.py — [mutating] Render the daily events into a self-contained HTML report.

Builds <workspace>/reports/<date>.html from events/<date>.json, diffs/<date>.json
(when present) and calendar/calendar.json. The page is designed for non-technical
readers: an intelligence-briefing masthead, stat tiles, one card per event with
the evidence pull-quote and screenshot, and a per-brand activity chart (inline
SVG). No external assets — it opens offline with a double click and prints
cleanly to PDF from the browser. Visual system: references/design-system.md.

Exit codes: 0 = report written, 1 = bad usage/missing events file.
Python 3.8+, standard library only.
"""

import argparse
import base64
import html
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import i18n  # noqa: E402

# event_type -> (ink text, tint background, stripe, i18n tag key). Colors are
# fixed by the design system; the label text comes from i18n per language.
TYPE_META = {
    "promo_start": ("#1f7a5a", "#e8f2ec", "#1f7a5a", "tag_new"),
    "promo_end": ("#a8452f", "#f6eae5", "#a8452f", "tag_ended"),
    "promo_update": ("#9a6a12", "#f5eddb", "#9a6a12", "tag_modified"),
    "other_change": ("#3d5350", "#eaeeec", "#3d5350", "tag_other"),
}

CSS = """
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
.wrap { max-width:760px; margin:0 auto; }

.masthead { border-top:3px solid var(--ink); padding-top:14px; margin-bottom:26px; }
.eyebrow { font-size:11px; letter-spacing:.18em; text-transform:uppercase;
  color:var(--petrol); font-weight:600; }
.masthead h1 { font-family:var(--serif); font-size:33px; line-height:1.08;
  font-weight:600; letter-spacing:-.01em; margin:6px 0 8px; text-wrap:balance; }
.masthead .meta { font-family:var(--mono); font-size:12px; color:var(--muted);
  border-top:1px solid var(--line); padding-top:8px; }

.kpis { display:grid; grid-template-columns:repeat(4,1fr); gap:1px;
  background:var(--line); border:1px solid var(--line); border-radius:12px;
  overflow:hidden; margin:0 0 30px; }
.kpi { background:var(--card); padding:16px 16px 14px; }
.kpi b { display:block; font-family:var(--mono); font-size:30px; font-weight:600;
  line-height:1; font-variant-numeric:tabular-nums; }
.kpi.hot b { color:var(--amber); }
.kpi span { display:block; font-size:10.5px; letter-spacing:.08em;
  text-transform:uppercase; color:var(--muted); margin-top:7px; }

h2 { font-family:var(--sans); font-size:12px; letter-spacing:.14em;
  text-transform:uppercase; color:var(--muted); font-weight:600;
  margin:30px 0 12px; padding-bottom:7px; border-bottom:1px solid var(--line);
  display:flex; align-items:center; gap:8px; }
h2::before { content:""; width:7px; height:7px; border-radius:2px;
  background:var(--petrol); display:inline-block; }

.card { background:var(--card); border:1px solid var(--line);
  border-left:3px solid var(--stripe,var(--petrol)); border-radius:10px;
  padding:16px 20px; margin-bottom:12px; page-break-inside:avoid; }
.tag { display:inline-block; font-size:10px; font-weight:700; letter-spacing:.06em;
  text-transform:uppercase; padding:4px 10px; border-radius:99px; margin-bottom:9px; }
.card h3 { font-family:var(--serif); font-size:20px; font-weight:600;
  line-height:1.2; margin-bottom:4px; text-wrap:balance; }
.card .disc { font-family:var(--mono); font-size:14px; font-weight:600; }
.card .brand { font-size:11px; letter-spacing:.06em; text-transform:uppercase;
  color:var(--faint); margin-bottom:9px; }
.card p { font-size:14px; color:#28352f; }
blockquote { font-family:var(--serif); font-style:italic; font-size:14.5px;
  color:var(--muted); border-left:2px solid var(--line); padding:2px 0 2px 14px;
  margin:12px 0; }
.card img { max-width:100%; border:1px solid var(--line); border-radius:6px;
  margin-top:12px; display:block; }

.panel { background:var(--card); border:1px solid var(--line);
  border-radius:10px; padding:18px 20px; overflow-x:auto; }
.panel .cap { font-size:11px; letter-spacing:.06em; text-transform:uppercase;
  color:var(--faint); margin-bottom:10px; }
.issues { background:#fbf3e3; border:1px solid #ecdcb4; border-radius:10px;
  padding:14px 18px; font-size:13px; color:#7a5c14; }
.empty { color:var(--muted); font-size:13.5px; font-style:italic; padding:2px; }
footer { font-family:var(--mono); text-align:center; color:var(--faint);
  font-size:10.5px; margin-top:34px; border-top:1px solid var(--line); padding-top:14px; }

@media print {
  body { background:#fff; padding:0; }
  .card,.panel,.kpis { border-color:#ccc; }
  h2 { break-after:avoid; }
}
"""


def esc(s):
    return html.escape(str(s or ""))


def event_card(ev, workspace, reports_dir, S):
    ink, bg, stripe, tag_key = TYPE_META.get(ev.get("event_type"), TYPE_META["other_change"])
    label = S[tag_key]
    disc = f' &middot; <span class="disc" style="color:{ink}">{esc(ev["discount"])}</span>' if ev.get("discount") else ""
    end = (ev.get("dates_seen") or {}).get("announced_end")
    end_html = f'<div class="brand">{esc(S["announced_end"].format(end=end))}</div>' if end else ""
    quote = f"<blockquote>« {esc(ev['evidence'])} »</blockquote>" if ev.get("evidence") else ""
    img = ""
    shot = ev.get("screenshot")
    if shot:
        shot_abs = (workspace / shot).resolve()
        if shot_abs.exists():
            suffix = shot_abs.suffix.lower()
            if suffix in (".png", ".jpg", ".jpeg", ".webp"):
                # Inline the capture as a data URI so the report is fully
                # self-contained — it survives being emailed, moved, or printed
                # to PDF with no broken image links. Files written as .png may
                # actually hold JPEG bytes (the Web Unlocker returns JPG), so
                # sniff the magic bytes rather than trusting the extension.
                raw = shot_abs.read_bytes()
                if raw[:3] == b"\xff\xd8\xff":
                    mime = "image/jpeg"
                elif raw[:8] == b"\x89PNG\r\n\x1a\n":
                    mime = "image/png"
                elif raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
                    mime = "image/webp"
                else:
                    mime = {".png": "image/png", ".webp": "image/webp"}.get(suffix, "image/jpeg")
                b64 = base64.b64encode(raw).decode("ascii")
                img = f'<img src="data:{mime};base64,{b64}" alt="capture">'
            else:
                # e.g. a full-page PDF from a stealth capture — link it, don't inline
                try:
                    src = "../" + shot_abs.relative_to(reports_dir.parent).as_posix()
                except ValueError:
                    src = shot_abs.as_uri()
                img = f'<a class="visual-link" href="{src}">📄 Voir le visuel ({shot_abs.suffix.lstrip(".").upper()})</a>'
    return f"""<div class="card" style="--stripe:{stripe}">
<span class="tag" style="color:{ink};background:{bg}">{label}</span>
<h3>{esc(ev.get('title', '(sans titre)'))}{disc}</h3>
<div class="brand">{esc(ev['brand'])} &middot; {esc(ev['country'])}</div>
{end_html}<p>{esc(ev.get('summary', ''))}</p>
{quote}{img}
</div>"""


def brand_chart(calendar, S):
    counts = Counter()
    for op in calendar.get("operations", []):
        if op.get("type") == "operation" and op.get("status") == "ongoing":
            counts[f"{op['brand']} {op['country']}"] += 1
    if not counts:
        return f'<p class="empty">{esc(S["chart_empty"])}</p>'
    top = counts.most_common(10)
    peak = max(c for _, c in top)
    rows, y = [], 0
    for name, c in top:
        w = int(470 * c / peak)
        rows.append(
            f'<text x="0" y="{y+15}" font-size="12.5" fill="#5c6b67" font-family="system-ui">{esc(name)}</text>'
            f'<rect x="180" y="{y+3}" width="{w}" height="16" rx="3" fill="#0f5f5c"></rect>'
            f'<text x="{188+w}" y="{y+16}" font-size="12" fill="#12211f" font-weight="600" font-family="ui-monospace,monospace">{c}</text>'
        )
        y += 28
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

    config_path = workspace / "watch.config.json"
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    lang = i18n.resolve_lang(config)
    S = i18n.strings(lang)

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
                issues.append(esc(S["fetch_failed"].format(slug=t["slug"], err=t.get("error", ""))))
    baseline = S["baseline"].format(b=esc(diff["baseline"])) if diff else ""

    sections = []
    for key, skey in [("promo_start", "sec_new"), ("promo_end", "sec_ended"),
                      ("promo_update", "sec_modified"), ("other_change", "sec_other")]:
        if by_type[key]:
            cards = "".join(event_card(e, workspace, reports_dir, S) for e in by_type[key])
            sections.append(f"<h2>{esc(S[skey])}</h2>{cards}")
    if not sections:
        sections.append(f'<h2>{esc(S["sec_result"])}</h2><p class="empty">{esc(S["no_change"])}</p>')
    issues_html = ""
    if issues:
        issues_html = f'<h2>{esc(S["sec_issues"])}</h2><div class="issues">' + "<br>".join(issues) + "</div>"

    page = f"""<!DOCTYPE html>
<html lang="{lang}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(S['report_eyebrow'])} — {esc(date)}</title><style>{CSS}</style></head>
<body><div class="wrap">
<div class="masthead">
<div class="eyebrow">{esc(S['report_eyebrow'])}</div>
<h1>{esc(S['report_title'].format(date=date))}</h1>
<div class="meta">{esc(S['report_meta'].format(baseline=baseline))}</div>
</div>
<div class="kpis">
<div class="kpi hot"><b>{len(by_type['promo_start'])}</b><span>{esc(S['kpi_new'])}</span></div>
<div class="kpi"><b>{len(by_type['promo_end'])}</b><span>{esc(S['kpi_ended'])}</span></div>
<div class="kpi"><b>{len(by_type['promo_update'])}</b><span>{esc(S['kpi_modified'])}</span></div>
<div class="kpi"><b>{ongoing}</b><span>{esc(S['kpi_market'])}</span></div>
</div>
{''.join(sections)}
{issues_html}
<h2>{esc(S['chart_title'])}</h2>
<div class="panel"><div class="cap">{esc(S['chart_cap'])}</div>{brand_chart(calendar, S)}</div>
<footer>{esc(S['footer'])}</footer>
</div></body></html>"""

    out = reports_dir / f"{date}.html"
    out.write_text(page, encoding="utf-8")
    print(f"report written: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
