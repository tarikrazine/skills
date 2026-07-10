#!/usr/bin/env python3
"""update_calendar.py — [mutating] Apply agent-classified events to the commercial calendar.

Reads an events JSON file (produced by the agent from the daily diff), merges it
into <workspace>/calendar/calendar.json, archives referenced screenshots into
<workspace>/calendar/visuals/, and re-renders <workspace>/calendar/calendar.md.

Lifecycle rules:
  promo_start  -> opens a new operation (or refreshes last_seen if an open
                  operation with the same brand/country/title already exists)
  promo_update -> appends an update to the matching open operation
  promo_end    -> closes the matching open operation (ended_on = event date)
  other_change -> recorded in the operations log as a one-day note

Exit codes: 0 = calendar updated, 1 = bad usage/input.
Python 3.8+, standard library only.
"""

import argparse
import datetime
import json
import re
import shutil
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

VALID_TYPES = {"promo_start", "promo_end", "promo_update", "other_change"}


def norm_title(title):
    """Normalize a title for matching: lowercase, no accents, collapsed spaces."""
    t = unicodedata.normalize("NFKD", title or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", t.lower()).strip()


def load_calendar(path):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"ERROR: calendar.json unreadable ({exc}); refusing to overwrite")
    return {"operations": []}


def find_open_op(calendar, brand, country, title):
    key = norm_title(title)
    for op in reversed(calendar["operations"]):
        if (
            op["status"] == "ongoing"
            and op["brand"] == brand
            and op["country"] == country
            and norm_title(op["title"]) == key
        ):
            return op
    return None


def next_id(calendar):
    return 1 + max((op["id"] for op in calendar["operations"]), default=0)


def archive_visual(workspace, visuals_dir, screenshot_rel, date, slug_hint):
    """Copy an event's screenshot into calendar/visuals/; returns relative path or None."""
    if not screenshot_rel:
        return None
    src = (workspace / screenshot_rel).resolve()
    if not src.exists():
        return None
    dest_name = f"{date}-{slug_hint}{src.suffix or '.png'}"
    dest = visuals_dir / dest_name
    shutil.copyfile(src, dest)
    return f"visuals/{dest_name}"


def slugify(value):
    value = norm_title(value)
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")[:60] or "op"


def apply_event(calendar, event, workspace, visuals_dir):
    brand, country = event["brand"], event["country"]
    etype, title = event["event_type"], event.get("title") or "(untitled)"
    date = event["date"]
    slug_hint = f"{slugify(brand)}-{slugify(country)}-{slugify(title)}"
    visual = archive_visual(workspace, visuals_dir, event.get("screenshot"), date, slug_hint)

    if etype in ("promo_start", "other_change"):
        existing = find_open_op(calendar, brand, country, title) if etype == "promo_start" else None
        if existing:
            existing["last_seen"] = max(existing["last_seen"], date)
            if visual and visual not in existing["visuals"]:
                existing["visuals"].append(visual)
            return "refreshed", existing["id"]
        op = {
            "id": next_id(calendar),
            "brand": brand,
            "country": country,
            "type": "operation" if etype == "promo_start" else "note",
            "title": title,
            "summary": event.get("summary", ""),
            "discount": event.get("discount"),
            "first_seen": date,
            "last_seen": date,
            "ended_on": date if etype == "other_change" else None,
            "announced_end": (event.get("dates_seen") or {}).get("announced_end"),
            "status": "ongoing" if etype == "promo_start" else "noted",
            "updates": [],
            "evidence": event.get("evidence", ""),
            "visuals": [visual] if visual else [],
        }
        calendar["operations"].append(op)
        return "opened" if etype == "promo_start" else "noted", op["id"]

    target = find_open_op(calendar, brand, country, title)
    if target is None:
        # promo_end/update without a tracked start: record as a closed operation
        op = {
            "id": next_id(calendar),
            "brand": brand, "country": country, "type": "operation",
            "title": title, "summary": event.get("summary", ""),
            "discount": event.get("discount"),
            "first_seen": date, "last_seen": date, "ended_on": date,
            "announced_end": (event.get("dates_seen") or {}).get("announced_end"),
            "status": "ended", "updates": [],
            "evidence": event.get("evidence", ""),
            "visuals": [visual] if visual else [],
        }
        calendar["operations"].append(op)
        return "closed-untracked", op["id"]
    if etype == "promo_update":
        target["updates"].append({"date": date, "summary": event.get("summary", "")})
        target["last_seen"] = max(target["last_seen"], date)
        if event.get("discount"):
            target["discount"] = event["discount"]
        if visual and visual not in target["visuals"]:
            target["visuals"].append(visual)
        return "updated", target["id"]
    # promo_end
    target["status"] = "ended"
    target["ended_on"] = date
    target["last_seen"] = max(target["last_seen"], date)
    if visual and visual not in target["visuals"]:
        target["visuals"].append(visual)
    return "closed", target["id"]


def ics_escape(text):
    return (str(text or "").replace("\\", "\\\\").replace(";", "\\;")
            .replace(",", "\\,").replace("\n", "\\n"))


def render_ics(calendar):
    """iCalendar export — import the file into Google Calendar/Outlook to see
    every competitor operation as an all-day event range. UIDs are stable per
    operation id, so re-importing updates events instead of duplicating them
    in clients that honor UID."""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//competitor-homepage-watch//EN",
        "CALSCALE:GREGORIAN",
        "X-WR-CALNAME:Veille concurrentielle",
    ]
    for op in calendar["operations"]:
        if op.get("type") != "operation":
            continue
        start = op["first_seen"].replace("-", "")
        end_date = op.get("ended_on") or op.get("announced_end") or op.get("last_seen")
        # DTEND is exclusive for all-day events: add one day
        y, m, d = (int(x) for x in end_date.split("-"))
        end = (datetime.date(y, m, d) + datetime.timedelta(days=1)).strftime("%Y%m%d")
        if end <= start:
            end = (datetime.date(*[int(x) for x in op["first_seen"].split("-")])
                   + datetime.timedelta(days=1)).strftime("%Y%m%d")
        title = f"[{op['brand']} {op['country']}] {op['title']}"
        if op.get("discount"):
            title += f" ({op['discount']})"
        desc = op.get("summary", "")
        if op.get("evidence"):
            desc += f"\nSource: « {op['evidence']} »"
        if op.get("status") == "ongoing":
            desc += "\nStatut: en cours (fin non observée)"
        lines += [
            "BEGIN:VEVENT",
            f"UID:op-{op['id']}@competitor-homepage-watch",
            f"DTSTAMP:{start}T000000Z",
            f"DTSTART;VALUE=DATE:{start}",
            f"DTEND;VALUE=DATE:{end}",
            f"SUMMARY:{ics_escape(title)}",
            f"DESCRIPTION:{ics_escape(desc)}",
            "TRANSP:TRANSPARENT",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def render_markdown(calendar):
    lines = ["# Commercial calendar", ""]
    by_key = defaultdict(list)
    for op in calendar["operations"]:
        by_key[(op["brand"], op["country"])].append(op)

    lines.append("## Operations by brand")
    for (brand, country) in sorted(by_key):
        lines += ["", f"### {brand} ({country})", ""]
        lines.append("| Operation | Discount | First seen | Ended | Status |")
        lines.append("|---|---|---|---|---|")
        for op in sorted(by_key[(brand, country)], key=lambda o: o["first_seen"]):
            end = op["ended_on"] or op["announced_end"] or "—"
            lines.append(
                f"| {op['title']} | {op.get('discount') or '—'} | {op['first_seen']} | {end} | {op['status']} |"
            )

    lines += ["", "## Month grid (all brands)", ""]
    months = defaultdict(list)
    for op in calendar["operations"]:
        if op["type"] != "operation":
            continue
        start_month = op["first_seen"][:7]
        end_month = (op["ended_on"] or op["last_seen"])[:7]
        month = start_month
        while month <= end_month:
            months[month].append(op)
            year, mon = int(month[:4]), int(month[5:7])
            month = f"{year + (mon == 12):04d}-{(mon % 12) + 1:02d}"
    for month in sorted(months):
        lines += ["", f"### {month}", ""]
        for op in sorted(months[month], key=lambda o: (o["brand"], o["country"])):
            end = op["ended_on"] or op["announced_end"] or "ongoing"
            lines.append(f"- **{op['brand']} {op['country']}** — {op['title']} ({op['first_seen']} → {end})")
    lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--workspace", required=True, help="watch workspace directory")
    ap.add_argument("--events", required=True, help="events JSON file for one day")
    args = ap.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    events_path = Path(args.events).expanduser().resolve()
    try:
        events = json.loads(events_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read events {events_path}: {exc}", file=sys.stderr)
        return 1
    # Accept both the bare list and the richer {"synthesis": ..., "events": [...]}
    # object that render_report also consumes.
    if isinstance(events, dict):
        events = events.get("events") or []
    if not isinstance(events, list):
        print("ERROR: events file must be a JSON array (or an object with an 'events' array)", file=sys.stderr)
        return 1

    calendar_dir = workspace / "calendar"
    visuals_dir = calendar_dir / "visuals"
    visuals_dir.mkdir(parents=True, exist_ok=True)
    calendar_path = calendar_dir / "calendar.json"
    calendar = load_calendar(calendar_path)

    for i, event in enumerate(events):
        missing = [k for k in ("brand", "country", "event_type", "date") if not event.get(k)]
        if missing:
            print(f"ERROR: event #{i} missing {missing}", file=sys.stderr)
            return 1
        if event["event_type"] not in VALID_TYPES:
            print(f"ERROR: event #{i} has invalid event_type {event['event_type']!r}", file=sys.stderr)
            return 1

    for event in events:
        action, op_id = apply_event(calendar, event, workspace, visuals_dir)
        print(f"{action:<16} #{op_id} {event['brand']}/{event['country']}: {event.get('title', '')}")

    calendar_path.write_text(json.dumps(calendar, indent=2, ensure_ascii=False), encoding="utf-8")
    (calendar_dir / "calendar.md").write_text(render_markdown(calendar), encoding="utf-8")
    (calendar_dir / "calendar.ics").write_text(render_ics(calendar), encoding="utf-8")
    ongoing = sum(1 for op in calendar["operations"] if op["status"] == "ongoing")
    print(f"calendar: {len(calendar['operations'])} operations total, {ongoing} ongoing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
