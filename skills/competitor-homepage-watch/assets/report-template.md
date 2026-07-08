# Competitive watch — {DATE}

Baseline: {BASELINE_DATE} · Targets: {N_OK} fetched, {N_FAILED} failed · Engine: {ENGINE}

## 🆕 New operations

<!-- One block per promo_start event. Omit the section if empty. -->
### {BRAND} ({COUNTRY}) — {TITLE}
- **Offer:** {SUMMARY} {DISCOUNT}
- **Announced end:** {ANNOUNCED_END or "not stated"}
- **Evidence:** "{EVIDENCE}"
- **Visual:** {SCREENSHOT_PATH or "n/a"}

## 🔚 Ended operations

<!-- One line per promo_end event: brand, country, title, observed duration. -->
- **{BRAND} ({COUNTRY})** — {TITLE} (seen {FIRST_SEEN} → {ENDED_ON}{, announced through ANNOUNCED_END})

## ✏️ Modified operations

<!-- One line per promo_update event: what changed. -->
- **{BRAND} ({COUNTRY})** — {TITLE}: {WHAT_CHANGED}

## 📋 Other notable changes

<!-- other_change events + one-line mentions of near-signal noise worth a human glance. -->

## ⚠️ Monitoring issues

<!-- fetch_failed targets, degraded fetches (consent walls, thin HTTP fallback), repeated failures. Omit if clean. -->
