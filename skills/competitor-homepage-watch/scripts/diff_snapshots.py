#!/usr/bin/env python3
"""diff_snapshots.py — [read-only] Block-level diff between two snapshot days.

Compares each target's normalized page.md between a baseline day and a newer day,
and emits a JSON document of added / removed / changed content blocks per target.
Obvious noise blocks (cookie banners, generic nav words) are pre-filtered but the
final judgment on what constitutes a commercial event belongs to the agent.

Usage:
  diff_snapshots.py <workspace> [--date YYYY-MM-DD] [--baseline YYYY-MM-DD] [--out diff.json]
  diff_snapshots.py --prev <dir> --today <dir> [--out diff.json]

Without --baseline, the most recent snapshot day before --date (default today) is used.
Exit codes: 0 = diff produced, 1 = bad usage, 3 = nothing to compare (fewer than 2 days).
Python 3.8+, standard library only.
"""

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

# Blocks matching these patterns are near-certain noise on any retail homepage.
# Keep the list short and conservative — the agent filters the rest with context.
NOISE_PATTERNS = [
    r"^\[?image:?\s*\]?$",
    r"\bcookies?\b.*\b(accept|consent|refus|reject|param|prefer|manage|polic|politique)",
    r"\b(accept|consent|refus|reject|param|prefer|manage|polic|politique)\w*\b.*\bcookies?\b",
    r"^(accept|refuse|reject|accepter|refuser|tout accepter|tout refuser)( all)?$",
    r"^\d+ ?(articles?|résultats?|results?)$",
    r"^(©|copyright)\b",
]
NOISE_RE = [re.compile(p, re.IGNORECASE) for p in NOISE_PATTERNS]
DATE_STAMP_RE = re.compile(r"\b\d{1,2}[/.]\d{1,2}[/.]\d{2,4}\b")


def normalize_blocks(text):
    """Split page text into stable, comparable blocks."""
    blocks = []
    for raw in re.split(r"\n\s*\n", text):
        block = " ".join(raw.split()).strip()
        if len(block) < 3:
            continue
        if any(rx.search(block) for rx in NOISE_RE):
            continue
        blocks.append(block)
    # Drop exact duplicates while preserving order (repeated nav/footer chunks)
    seen, out = set(), []
    for b in blocks:
        if b not in seen:
            seen.add(b)
            out.append(b)
    return out


def diff_target(prev_text, today_text):
    prev_blocks = normalize_blocks(prev_text)
    today_blocks = normalize_blocks(today_text)
    sm = difflib.SequenceMatcher(a=prev_blocks, b=today_blocks, autojunk=False)
    added, removed, changed = [], [], []
    for op, a1, a2, b1, b2 in sm.get_opcodes():
        if op == "equal":
            continue
        if op == "replace":
            olds, news = prev_blocks[a1:a2], today_blocks[b1:b2]
            # Pair up replacements; leftovers become pure adds/removes
            for old, new in zip(olds, news):
                if difflib.SequenceMatcher(a=old, b=new).ratio() > 0.6:
                    changed.append({"before": old, "after": new})
                else:
                    removed.append(old)
                    added.append(new)
            removed.extend(olds[len(news):])
            added.extend(news[len(olds):])
        elif op == "delete":
            removed.extend(prev_blocks[a1:a2])
        elif op == "insert":
            added.extend(today_blocks[b1:b2])
    # A changed block that only differs by a date stamp is countdown noise
    changed = [
        c for c in changed
        if DATE_STAMP_RE.sub("<d>", c["before"]) != DATE_STAMP_RE.sub("<d>", c["after"])
    ]
    return added, removed, changed


def read_meta(target_dir):
    meta_path = target_dir / "meta.json"
    if meta_path.exists():
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("workspace", nargs="?", help="workspace dir containing snapshots/")
    ap.add_argument("--date", default=None, help="the 'today' snapshot day (default: latest)")
    ap.add_argument("--baseline", default=None, help="the baseline day (default: latest day before --date)")
    ap.add_argument("--prev", default=None, help="explicit baseline snapshot dir")
    ap.add_argument("--today", default=None, help="explicit today snapshot dir")
    ap.add_argument("--out", default=None, help="write diff JSON here (default: stdout)")
    args = ap.parse_args()

    if args.prev and args.today:
        prev_dir, today_dir = Path(args.prev).resolve(), Path(args.today).resolve()
    elif args.workspace:
        snaps = Path(args.workspace).expanduser().resolve() / "snapshots"
        days = sorted(d.name for d in snaps.iterdir() if d.is_dir()) if snaps.is_dir() else []
        if args.date and args.date not in days:
            print(f"ERROR: no snapshot for {args.date} in {snaps}", file=sys.stderr)
            return 1
        today_name = args.date or (days[-1] if days else None)
        earlier = [d for d in days if d < today_name] if today_name else []
        baseline_name = args.baseline or (earlier[-1] if earlier else None)
        if not today_name or not baseline_name:
            print("NOTHING-TO-COMPARE: need at least two snapshot days", file=sys.stderr)
            return 3
        prev_dir, today_dir = snaps / baseline_name, snaps / today_name
    else:
        ap.print_usage(sys.stderr)
        return 1

    result = {
        "baseline": prev_dir.name,
        "date": today_dir.name,
        "targets": [],
    }
    prev_slugs = {d.name for d in prev_dir.iterdir() if d.is_dir()}
    today_slugs = {d.name for d in today_dir.iterdir() if d.is_dir()}

    for slug in sorted(today_slugs | prev_slugs):
        meta = read_meta(today_dir / slug) or read_meta(prev_dir / slug)
        entry = {
            "slug": slug,
            "brand": meta.get("brand", slug),
            "country": meta.get("country", ""),
            "url": meta.get("url", ""),
            "status": None,
            "added": [], "removed": [], "changed": [],
        }
        today_page = today_dir / slug / "page.md"
        prev_page = prev_dir / slug / "page.md"
        if not today_page.exists():
            entry["status"] = "fetch_failed"
            entry["error"] = read_meta(today_dir / slug).get("error") or "no snapshot today"
        elif not prev_page.exists():
            entry["status"] = "new_target"
        else:
            added, removed, changed = diff_target(
                prev_page.read_text(encoding="utf-8"),
                today_page.read_text(encoding="utf-8"),
            )
            entry.update(added=added, removed=removed, changed=changed)
            entry["status"] = "changed" if (added or removed or changed) else "no_change"
        result["targets"].append(entry)
        detail = ""
        if entry["status"] == "changed":
            detail = f" (+{len(entry['added'])} added, -{len(entry['removed'])} removed, ~{len(entry['changed'])} changed)"
        print(f"{entry['status']:<13} {slug}{detail}")

    payload = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        out_path = Path(args.out).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload, encoding="utf-8")
        print(f"diff written: {out_path}")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
