---
name: competitor-homepage-watch
description: Monitors competitor homepages to track their commercial plans. Runs a daily crawl of configured competitor and own-brand homepages across countries, diffs each page against the previous snapshot, alerts on new and ended promotions or commercial operations, and archives every event into a commercial-plan calendar with screenshots for year-over-year analysis. Use whenever the user mentions competitive intelligence, competitor monitoring, promo or campaign tracking, homepage change detection, reconstructing a competitor's commercial calendar, or comparing this year's trade plan against last year's — even if they don't say "watch" or "crawl" explicitly. Don't use for one-off website scraping, SEO audits, full-site crawls, or price-per-product comparison.
---

# Competitor Homepage Watch

Track competitors' commercial plans through their homepages: fetch daily snapshots, detect what changed since the previous run, alert on new/ended operations, and build a commercial calendar that reconstructs each competitor's trade plan over time.

## How the pieces fit

Scripts handle the deterministic work; the agent handles the judgment:

| Step | Who | Tool |
|------|-----|------|
| Fetch homepages → snapshots | script | `scripts/fetch_homepage.py` **[mutating]** |
| Diff today vs previous snapshot | script | `scripts/diff_snapshots.py` **[read-only]** |
| Classify changes (promo start/end/noise) | **agent** | `references/promo-detection.md` |
| Write the daily alert report | **agent** | `assets/report-template.md` |
| Archive events into the calendar | script | `scripts/update_calendar.py` **[mutating]** |
| Answer analysis questions (plan N-1, comparisons) | **agent** | `references/calendar-format.md` |

All script paths below are relative to this skill's directory. Resolve `<skill-dir>` to the directory containing this SKILL.md before running commands. Scripts are Python 3 standard library only — no pip installs needed.

## Workspace layout

All data lives in a workspace directory chosen by the user (default `./competitor-watch`):

```
competitor-watch/
├── watch.config.json          # targets: brands × countries × URLs
├── snapshots/YYYY-MM-DD/      # one dir per day, one subdir per target
│   └── <brand>-<country>/     # page.md, page.html, screenshot.png, meta.json
├── diffs/YYYY-MM-DD.json      # machine diff for the day
├── events/YYYY-MM-DD.json     # agent-classified events for the day
├── reports/YYYY-MM-DD.md      # human alert report
└── calendar/
    ├── calendar.json          # cumulative event log (source of truth)
    ├── calendar.md            # rendered commercial calendar
    └── visuals/               # archived screenshots per event
```

## First-time setup

1. Ask the user where the workspace should live, then create it.
2. Copy `assets/watch.config.example.json` into the workspace as `watch.config.json`.
3. Interview the user for the real targets: each competitor brand, each country where it operates, and the exact homepage URL per country — plus the user's own brand sites (set `"own_brand": true`; tracking your own homepage keeps the calendar complete for later self-analysis). Read `references/config-schema.md` for every field and validation rules.
4. Check crawling capability: if the `FIRECRAWL_API_KEY` environment variable is set, fetches use Firecrawl (JavaScript rendering + full-page screenshots — the visuals that get archived). Without it, fetches fall back to plain HTTP text extraction: still functional, but no screenshots and JS-heavy pages may come back thin. Tell the user which mode is active and recommend a Firecrawl key for production use.
5. Run the first fetch (step 1 of the daily run below). The first day produces snapshots only — there is nothing to diff against yet. Say so rather than inventing a comparison.

## Daily run

Execute these steps in order. If the user asks for "the daily watch", "check competitors", or similar, this is the procedure.

### 1. Fetch today's snapshots

```bash
python3 <skill-dir>/scripts/fetch_homepage.py --config <workspace>/watch.config.json
```

The script writes `snapshots/<today>/` inside the workspace and prints one status line per target. Per-target failures never abort the batch — they are recorded in that target's `meta.json`. If a target fails repeatedly across days, surface it to the user (the URL may have moved).

### 2. Diff against the previous snapshot

```bash
python3 <skill-dir>/scripts/diff_snapshots.py <workspace> --out <workspace>/diffs/<today>.json
```

Without explicit dates the script compares today against the most recent earlier snapshot day. It prints a per-target summary (`no_change`, `changed`, `new_target`, `fetch_failed`) and writes block-level added/removed/changed content to the diff JSON. If every target is `no_change`, report "no commercial changes today" and stop — do not force events out of nothing.

### 3. Classify the changes (agent judgment)

Read the diff JSON. For each changed target, decide what each added/removed/changed block means. Read `references/promo-detection.md` for the classification rules, noise patterns (carousels, cookie banners, rotating seasonal words), and the event lifecycle. Produce `events/<today>.json`:

```json
[
  {
    "brand": "brandname", "country": "FR",
    "event_type": "promo_start",
    "title": "Winter tyres -30%",
    "summary": "Homepage hero now advertises 30% off winter tyres, ends Jan 31 per banner text.",
    "discount": "-30%",
    "dates_seen": {"announced_end": "2026-01-31"},
    "evidence": "the exact added text block",
    "screenshot": "snapshots/2026-07-08/brandname-fr/screenshot.png",
    "date": "2026-07-08"
  }
]
```

`event_type` is one of `promo_start`, `promo_end`, `promo_update`, `other_change`. Only genuine commercial signals become events — layout tweaks and noise are dropped (mention them in one line of the report if notable).

### 4. Write the daily alert report

Fill `assets/report-template.md` into `reports/<today>.md`: new operations first, then ended ones, then modifications, grouped by brand and country, each with its evidence quote and screenshot reference. Present the report content in the conversation — this IS the alert. If the user has an alerting channel (email, Slack, n8n webhook), offer to send it there; see `references/scheduling.md` for wiring options.

### 5. Archive into the commercial calendar

```bash
python3 <skill-dir>/scripts/update_calendar.py --workspace <workspace> --events <workspace>/events/<today>.json
```

The script appends events to `calendar/calendar.json` (a `promo_end` closes the matching open operation), copies referenced screenshots into `calendar/visuals/`, and re-renders `calendar/calendar.md`. Never edit `calendar.json` by hand — always go through the script so the lifecycle stays consistent.

## Analysis mode

When the user asks questions like "what did competitor X run last November", "reconstruct Y's commercial plan for 2025", or "what was everyone doing at this time last year" — read `calendar/calendar.json` and answer from it. Read `references/calendar-format.md` for the schema and ready-made analysis recipes (per-brand timeline, month-by-month cross-brand grid, N-1 comparison for next year's trade planning).

## Automating the daily run

The daily run is designed to be scheduled. Read `references/scheduling.md` for the three supported setups: cron + `claude -p`, Claude Code scheduled routines, and n8n. Recommend scheduling once the user has validated two or three manual runs.

## Edge cases worth knowing

- **First run / new target**: no previous snapshot exists — the diff reports `new_target`; record a single `other_change` event noting monitoring started, not a fake promo.
- **Gaps** (skipped weekend, failed day): the diff compares against the most recent available day, so nothing is lost; date ranges in events just get wider. Say which baseline day was used.
- **Redesigns**: a homepage relaunch produces a massive diff. Don't emit dozens of events — emit one `other_change` ("site redesign") plus only the clearly commercial operations visible on the new page.
- **Consent walls and bot protection**: if `page.md` is mostly a cookie/consent wall or a "enable JavaScript / ad blocker" message, the fetch engine couldn't see the real page — the fetch script marks these `suspected_blocked` in `meta.json` and in its output. Flag the target as degraded rather than reporting "everything was removed". Retail sites behind DataDome-class protection reject plain HTTP entirely (403) and may even block default Firecrawl scrapes: set `"firecrawl": {"proxy": "stealth"}` on that target in the config (see `references/config-schema.md`).
