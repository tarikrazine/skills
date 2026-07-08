# Commercial calendar — schema and analysis recipes

`calendar/calendar.json` is the cumulative source of truth; `calendar.md` is a
rendered view regenerated on every `update_calendar.py` run. Answer analysis
questions from the JSON, not from the markdown.

## calendar.json schema

```json
{
  "operations": [
    {
      "id": 12,
      "brand": "BrandA",
      "country": "FR",
      "type": "operation",            // "operation" (a promo/campaign) or "note" (other_change)
      "title": "Winter tyres -30%",
      "summary": "30% off winter tyres, announced through Jan 31.",
      "discount": "-30%",
      "first_seen": "2026-01-05",     // first daily run where it appeared
      "last_seen": "2026-01-28",      // last daily run where it was still there
      "ended_on": "2026-01-29",       // first run where it was gone (null while ongoing)
      "announced_end": "2026-01-31",  // end date stated on the page, if any
      "status": "ended",              // "ongoing" | "ended" | "noted"
      "updates": [ {"date": "2026-01-15", "summary": "discount deepened to -40%"} ],
      "evidence": "exact text block that triggered the event",
      "visuals": ["visuals/2026-01-05-branda-fr-winter-tyres-30.png"]
    }
  ]
}
```

Dates are observation dates from daily runs, so real start/end may precede
`first_seen` / follow `last_seen` by up to the run interval (plus any gap days).
`announced_end` is the page's own claim. Make this distinction explicit when
reporting durations.

## Analysis recipes

Answer directly from the JSON with these patterns (read the file, filter, present):

**Reconstruct one competitor's commercial plan for a year** — filter
`operations` by `brand` and `first_seen` year, `type == "operation"`, sort by
`first_seen`; present as a timeline table (operation, discount, observed period,
announced end, visuals). Include `own_brand` targets when the user wants "us vs
them" on one page.

**Month-by-month cross-brand grid (trade-plan view)** — an operation is active
in month M when `first_seen <= end-of-M` and `(ended_on or last_seen) >= start-of-M`.
The rendered `calendar.md` already contains this grid; rebuild it filtered when
the user narrows to a country or brand subset.

**N-1 comparison for next year's plan** — for a target month, list every brand's
active operations in that month last year: discount depth, themes, timing
(start relative to month), duration. The deliverable the user usually wants: a
per-month table "what did each competitor run in N-1" to position next year's
own operations against.

**Promo pressure** — count active operation-days per brand per quarter to
compare how aggressively each competitor promotes; useful for "who is the most
promotional" questions.

## Visuals

Screenshots referenced by operations live in `calendar/visuals/`, named
`<date>-<brand>-<country>-<title-slug>.png`. When presenting an analysis,
mention the visual paths so the user can pull the actual creative for a
moodboard or plan review; embed them when the output format supports images.

## Integrity rules

- Never edit `calendar.json` by hand; replay corrections as events through
  `update_calendar.py` (e.g. a missed end = emit `promo_end` with the right date).
- If the file is corrupted, the script refuses to run rather than overwrite —
  restore from git/backup or fix the JSON manually before rerunning.
- The calendar only knows what the daily runs saw. For history before
  monitoring started, a manual backfill is possible: fetch archived homepages
  (e.g. the Wayback Machine) into dated snapshot dirs and run the normal
  diff → classify → archive pipeline over consecutive archive dates.
