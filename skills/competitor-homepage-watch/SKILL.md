---
name: competitor-homepage-watch
description: Monitors competitor homepages to track their commercial plans. Runs a daily crawl of configured competitor and own-brand homepages across countries, diffs each page against the previous snapshot, alerts on new and ended promotions or commercial operations, and archives every event into a commercial-plan calendar with screenshots and Google Calendar (ICS) export for year-over-year analysis. Use whenever the user mentions competitive intelligence, competitor monitoring, promo or campaign tracking, homepage change detection, reconstructing a competitor's commercial calendar, or comparing this year's trade plan against last year's — even without the words "watch" or "crawl", including French phrasings like "lancer la veille", "veille concurrentielle" or "veille du jour". Don't use for one-off website scraping, SEO audits, full-site crawls, or price-per-product comparison.
---

# Competitor Homepage Watch

Track competitors' commercial plans through their homepages: fetch daily snapshots, detect what changed since the previous run, alert on new/ended operations, and build a commercial calendar that reconstructs each competitor's trade plan over time.

## How the pieces fit

Scripts handle the deterministic work; the agent handles the judgment:

| Step | Who | Tool |
|------|-----|------|
| Bootstrap a new workspace | script | `scripts/init_workspace.py` **[bootstrap]** |
| Fetch homepages → snapshots | script | `scripts/fetch_homepage.py` **[mutating]** |
| Capture visuals for bot-protected sites (optional) | script | `scripts/capture_visual.py` **[mutating]** |
| Diff today vs previous snapshot | script | `scripts/diff_snapshots.py` **[read-only]** |
| Classify changes (promo start/end/noise) | **agent** | `references/promo-detection.md` |
| Write the daily alert report | **agent** | `assets/report-template.md` |
| Render the reader-friendly HTML report | script | `scripts/render_report.py` **[mutating]** |
| Archive events into the calendar (+ ICS export) | script | `scripts/update_calendar.py` **[mutating]** |
| Build the cumulative monthly dashboard (optional) | script | `scripts/build_dashboard.py` **[mutating]** |
| Answer analysis questions (plan N-1, comparisons) | **agent** | `references/calendar-format.md` |

**Daily report vs dashboard — keep them distinct.** The daily HTML report
(`reports/<date>.html`) shows only what CHANGED versus the previous day. The
dashboard (`dashboard.html`) is a CUMULATIVE view of every operation active in a
window (a calendar month by default) as a Gantt timeline — the market's
commercial plan at a glance. The daily run always produces the report; the
dashboard is generated on demand (or offered at the end of a run).

All script paths below are relative to this skill's directory. Resolve `<skill-dir>` to the directory containing this SKILL.md before running commands. Scripts are Python 3 standard library only — no pip installs needed.

**Visual consistency (read before any HTML output).** The reports and dashboard are rendered by scripts with fixed styling, so they look identical across model versions. If you ever modify a rendering script, or generate any ad-hoc visual (e.g. a custom comparison view in analysis mode), follow `references/design-system.md` and reuse its tokens — do not invent a new palette or layout. Every visual this skill emits must read as another page of the same product, regardless of which model is running.

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

1. Ask the user where the workspace should live, then bootstrap it in one command:
   ```bash
   python3 <skill-dir>/scripts/init_workspace.py --dir <workspace>
   ```
   This creates the directory tree, installs a starter config, and writes a
   `CLAUDE.md` into the workspace that maps everyday phrases ("lancer la
   veille", "run the daily watch") to the full daily procedure — so future
   sessions in that directory trigger the run without re-explaining anything.
2. **Guide the user by the hand** — many users are non-technical, so don't just
   name files, offer to open them (macOS `open`, Linux `xdg-open`, Windows
   `explorer`):
   - Offer to open the workspace folder in their file manager so they see
     where everything lives: `open <workspace>`.
   - Offer to open the config for editing (`open -t <workspace>/watch.config.json`
     or their editor) and fill the brands/countries/URLs together while it's
     open in front of them.
   - If `FIRECRAWL_API_KEY` is missing, explain it comes from firecrawl.dev →
     API Keys, then offer to add the export line to their shell profile for
     them (`echo 'export FIRECRAWL_API_KEY="fc-..."' >> ~/.zshrc`) — with their
     confirmation, never silently. Verify afterwards with a one-target fetch.
   - Do NOT mention Browser Use / `BROWSER_USE_API_KEY` at setup unless the
     config already enables `screenshot_engine: "browser-use"` on some target.
     It's an optional add-on only for visuals on bot-protected sites; surface it
     later, once, per the soft-suggestion rule in the daily run — not upfront.
     When it IS needed, the setup mirrors Firecrawl: browser-use.com → API key →
     `export BROWSER_USE_API_KEY="..."` with the user's confirmation.
3. The starter config is a copy of `assets/watch.config.example.json`. Ask the
   user which **output language** the reports and dashboard should be written in
   — `fr`, `en`, or `es` — and set `"language"` in the config. This is the
   language of *their* reports, independent of the languages of the competitor
   sites they watch; a French team can watch German and Spanish homepages and
   still get French reports. See `references/config-schema.md`.
4. Interview the user for the real targets: each competitor brand, each country where it operates, and the exact homepage URL per country — plus the user's own brand sites (set `"own_brand": true`; tracking your own homepage keeps the calendar complete for later self-analysis). Read `references/config-schema.md` for every field and validation rules.
4. Check crawling capability: if the `FIRECRAWL_API_KEY` environment variable is set, fetches use Firecrawl (JavaScript rendering + full-page screenshots — the visuals that get archived). Without it, fetches fall back to plain HTTP text extraction: still functional, but no screenshots and JS-heavy pages may come back thin. Tell the user which mode is active and recommend a Firecrawl key for production use. **Screenshot caveat:** each snapshot records a `screenshot_status` in `meta.json`. On standard sites Firecrawl captures a full-page screenshot (`captured`). On sites behind DataDome-class bot protection, the fetch escalates to Firecrawl's enhanced engine to read the content — but that engine **cannot take screenshots** (`unsupported-on-protected-site`). So the text/commercial reading always works on protected competitors; the visual is available only for competitors that don't need the enhanced engine. Set this expectation with the user rather than promising a screenshot for every target.
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

Fill `assets/report-template.md` into `reports/<today>.md`: new operations first, then ended ones, then modifications, grouped by brand and country, each with its evidence quote and screenshot reference. Present the report content in the conversation — this IS the alert.

Then render the reader-friendly version for non-technical stakeholders:

```bash
python3 <skill-dir>/scripts/render_report.py --workspace <workspace> --date <today>
```

This produces `reports/<today>.html` — a self-contained page (KPIs, event cards with evidence and screenshots, per-brand activity chart) that opens with a double click and prints cleanly to PDF. Offer to open it (`open reports/<today>.html` on macOS). If the user has an alerting channel (email, Slack, n8n webhook), offer to send the report there; see `references/scheduling.md` for wiring options.

### 4b. Capture visuals for bot-protected sites — OPT-IN, config-gated

This step is **off by default** and must stay invisible unless the user has
explicitly enabled it. Run `capture_visual.py` for a target **only if ALL** of
these hold:
- the target has `"screenshot_engine": "browser-use"` in `watch.config.json`, AND
- `BROWSER_USE_API_KEY` is set in the environment, AND
- that target's `meta.json` shows `screenshot_status: unsupported-on-protected-site`.

If any is false, do nothing about visuals for that target and don't mention
Browser Use — the text/commercial reading already works. When all hold:

```bash
python3 <skill-dir>/scripts/capture_visual.py --url <target-url> \
  --out <workspace>/snapshots/<today>/<slug>/screenshot.png --country <cc>
```

It costs a few cents per capture (residential proxy + CAPTCHA solving), takes
30–90s, and may still be blocked on the hardest sites — on exit code 2, leave
the target text-only and say so once. After a `screenshot.png` is saved, the
event's `screenshot` field references it like any other.

**Soft suggestion (at most once, max 2 targets).** If there are protected
targets flagged `unsupported-on-protected-site` that do NOT have
`screenshot_engine` set, you may mention **once** — not every run — that visuals
for up to the two most important of them can be enabled via Browser Use (free
tier + a few cents per capture), and offer the setup guide. Never enable it
yourself, never nag, and cap the suggestion at 2 targets to control cost. If the
user isn't interested, drop it and don't raise it again.

### 5. Archive into the commercial calendar

```bash
python3 <skill-dir>/scripts/update_calendar.py --workspace <workspace> --events <workspace>/events/<today>.json
```

The script appends events to `calendar/calendar.json` (a `promo_end` closes the matching open operation), copies referenced screenshots into `calendar/visuals/`, and re-renders both `calendar/calendar.md` and `calendar/calendar.ics`. The `.ics` file imports into Google Calendar or Outlook — every competitor operation appears as an all-day event range, so the commercial plan can be read in a real calendar app; UIDs are stable, so re-importing updates instead of duplicating. When the user asks about Google Calendar, don't just point at the file: reveal it in their file manager (`open -R <workspace>/calendar/calendar.ics` on macOS) and walk them through the import (calendar.google.com → Settings → Import & export → Import, ideally into a dedicated "Veille concurrence" calendar). Never edit `calendar.json` by hand — always go through the script so the lifecycle stays consistent.

## Cumulative dashboard (on demand)

When the user wants the big picture rather than today's diff — "montre le
tableau de bord", "le plan du mois", "vue d'ensemble", "dashboard" — build it:

```bash
python3 <skill-dir>/scripts/build_dashboard.py --workspace <workspace> --month <YYYY-MM>
```

Use `--month YYYY-MM` for a calendar month (default: the latest month with
activity) or `--days N` for a rolling window. It writes `dashboard.html` — a
Gantt timeline of every operation active in the window, KPIs, and a per-brand
breakdown. Offer to open it (`open dashboard.html`). It's also a natural thing
to offer at the end of a daily run ("veux-tu la vue d'ensemble du mois ?").

## Analysis mode

When the user asks questions like "what did competitor X run last November", "reconstruct Y's commercial plan for 2025", or "what was everyone doing at this time last year" — read `calendar/calendar.json` and answer from it. If the answer is best delivered as a visual (a custom table or chart the two scripts don't already produce), generate self-contained HTML that follows `references/design-system.md` so it matches the report and dashboard. Read `references/calendar-format.md` for the schema and ready-made analysis recipes (per-brand timeline, month-by-month cross-brand grid, N-1 comparison for next year's trade planning).

## Automating the daily run

The daily run is designed to be scheduled. Read `references/scheduling.md` for the three supported setups: cron + `claude -p`, Claude Code scheduled routines, and n8n. Recommend scheduling once the user has validated two or three manual runs.

## Edge cases worth knowing

- **First run / new target**: no previous snapshot exists — the diff reports `new_target`; record a single `other_change` event noting monitoring started, not a fake promo.
- **Gaps** (skipped weekend, failed day): the diff compares against the most recent available day, so nothing is lost; date ranges in events just get wider. Say which baseline day was used.
- **Redesigns**: a homepage relaunch produces a massive diff. Don't emit dozens of events — emit one `other_change` ("site redesign") plus only the clearly commercial operations visible on the new page.
- **Consent walls and bot protection**: if `page.md` is mostly a cookie/consent wall or a "enable JavaScript / ad blocker" message, the fetch engine couldn't see the real page — the fetch script marks these `suspected_blocked` in `meta.json` and in its output. Flag the target as degraded rather than reporting "everything was removed". Retail sites behind DataDome-class protection reject plain HTTP entirely (403) and serve a fake "enable JS" page (HTTP 200) to default Firecrawl scrapes — the fetch script detects this and automatically retries once with Firecrawl's enhanced proxies. For known-protected targets, set `"firecrawl": {"proxy": "enhanced"}` in the config to skip the wasted first attempt (see `references/config-schema.md`).
