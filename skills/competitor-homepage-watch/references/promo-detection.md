# Classifying homepage changes into commercial events

The diff JSON gives added / removed / changed text blocks per target. The job is
to turn those into commercial events — and only commercial events. When unsure,
prefer fewer, higher-confidence events: a calendar polluted with noise is worse
than one that misses a minor banner.

## Event types

| `event_type` | Emit when |
|---|---|
| `promo_start` | A commercial operation appears that wasn't there before: discount, sale, themed operation ("Winter days"), bundle, financing offer ("3× free"), loyalty boost, contest, seasonal campaign with commercial intent. |
| `promo_end` | A previously tracked operation disappears from the page. Match it to the open operation in `calendar/calendar.json` by brand/country/title before emitting — use the same `title` so the calendar closes the right one. |
| `promo_update` | A tracked operation is still there but its terms changed: discount deepened (-20% → -30%), end date extended, mechanics changed. |
| `other_change` | Commercially relevant but not an operation: new service line launched, price-positioning claim ("lowest price guaranteed"), store-opening announcement, site redesign (one single event), monitoring started for a new target. |

## What is signal

Strong promo markers, in any language: percentages and amounts off (`-30%`,
`50€ offerts`, `2+1`), urgency words (`jusqu'au`, `until`, `derniers jours`,
`solde`, `sale`, `Black Friday`, `offre`, `promo`, `deal`, `bis zu`, `Rabatt`,
`descuento`), operation names in title case, date ranges, promo codes.
An added block with a discount marker + a date is almost certainly `promo_start`.

Also treat as signal: hero-banner text swaps (the hero is the retailer's main
commercial slot), `[image: ...]` alt-text changes describing an offer, new
countdown or voucher mechanics.

## What is noise — do not emit events for

- Cookie/consent, newsletter, app-download, login/account blocks.
- Carousel rotation: the same set of offers reordered. Compare added vs removed
  lists — if a "removed" block reappears in "added" with trivial differences,
  it moved, it didn't start or end.
- Rotating editorial content: blog teasers, advice articles, weather-driven
  copy, review counts, star ratings, stock counters.
- Pure countdown ticks and date stamps (the diff script already strips blocks
  whose only difference is a date, but some slip through in reworded form).
- Legal/footer text, delivery-conditions tweaks, cosmetic rewording with no
  commercial delta.

## Lifecycle discipline

An operation's life is: `promo_start` (first seen) → optional `promo_update`s →
`promo_end` (first day it's gone). Two consequences:

1. **Check the calendar before classifying.** Read `calendar/calendar.json`
   ongoing operations for that brand/country. A block that looks "new" may be a
   tracked operation whose wording shifted — that's `promo_update`, not a new
   start. A removed block that matches an ongoing operation is its `promo_end`.
2. **Reuse exact titles.** `update_calendar.py` matches `promo_end`/`promo_update`
   to open operations by normalized title equality. Copy the title from the
   calendar entry when closing or updating it.

## Extracting dates

Fill `dates_seen.announced_end` when the page states an end date ("jusqu'au 31
janvier" → `"2026-01-31"`, resolving the year from context). Never invent dates:
the observed `first_seen`/`ended_on` from the daily runs are the ground truth;
announced dates are a bonus. If a promo announces its end date, note that the
calendar can show the operation as planned through that date even if a fetch
gap hides the exact last day.

## Redesigns and degraded fetches

- Massive diff on one target (most blocks added AND removed): treat as a
  redesign. Emit one `other_change` event, then only the clearly commercial
  operations readable on the new page. Following days will diff cleanly again.
- `page.md` dominated by consent-wall text, or `meta.json` shows the HTTP
  fallback on a JS-heavy site: the fetch is degraded, not the competitor's page
  emptied. Emit nothing; flag the target in the report's issues line and suggest
  a Firecrawl key if the fallback engine is the cause.

## Screenshots (visuals) on protected sites

When building an event, only set `screenshot` if the target's snapshot actually
has one. Check `meta.json`'s `screenshot_status`: `captured` means a
`screenshot.png` exists and you should reference it; `unsupported-on-protected-site`
means the competitor is behind DataDome-class protection and Firecrawl's enhanced
engine could not capture a visual (the text WAS captured — this is expected, not
an error). For those events, leave `screenshot` null and don't apologize for it
in the report — the evidence quote carries the signal. Mention in the report's
issues line, once, which brands can't be screenshotted so the user knows why some
calendar entries have no visual.
