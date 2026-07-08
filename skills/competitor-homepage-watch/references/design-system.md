# Design system — visual output rules

Every visual artifact this skill produces (daily HTML report, monthly dashboard,
and any ad-hoc HTML view the agent generates in analysis mode) MUST look like it
came from the same product. This file is the single source of truth for that
look. The bundled scripts (`render_report.py`, `build_dashboard.py`) already
encode these exact values — read this before modifying a script or generating
any new visual, and reuse these tokens rather than inventing a palette.

Why this matters: the model that runs this skill will change over time, and each
model has its own default aesthetic. Pinning the tokens here keeps every report
consistent across model versions and across the two scripts.

## Design tokens (light theme — see note)

**Palette**

| Token | Hex | Use |
|---|---|---|
| `--navy` | `#0f2a43` | Header background, headings, primary text emphasis |
| `--blue` | `#1d4e79` | Primary accent: chart bars, links, headings level 3 |
| `--ink` | `#1f2733` | Body text |
| `--muted` | `#5b6b7c` | Secondary text, labels |
| `--faint` | `#8b98a7` | Footnotes, axis ticks |
| `--page` | `#f2f4f7` | Page background |
| `--surface` | `#ffffff` | Cards, panels |
| `--border` | `#e3e8ee` | Card/table borders |
| `--header-sub` | `#b9c8d8` | Subtitle text on the navy header |

**Semantic colors** (event types — text on tint, never used as the accent):

| Meaning | Text | Tint background |
|---|---|---|
| New operation (`promo_start`) | `#0e7a4a` | `#e6f5ee` |
| Ended operation (`promo_end`) | `#a33b3b` | `#faecec` |
| Modified operation (`promo_update`) | `#8a6d1a` | `#faf4e0` |
| Other change (`other_change`) | `#41586e` | `#eef2f6` |
| Warning / issues panel | `#6b5a1a` | `#fff8e6`, border `#e8d9a0` |

**Brand series palette** (Gantt rows, cycled by brand+country, in order):
`#1d4e79`, `#0e7a4a`, `#a3521a`, `#7a3fb8`, `#0f7d8a`, `#b03b5a`, `#5a6b1a`, `#8a6d1a`.
Assign deterministically by sorted brand+country so a brand keeps its color
across runs.

**Typography**
- Family: `"Helvetica Neue", Arial, sans-serif` (system-safe; no web fonts — the
  reports must open offline).
- Scale: page title 20–22px/600; section `h2` 15px; sub-head `h3` 13px; body
  13px; captions/labels 11–12px. Numbers in KPIs 26px.
- Use `font-variant-numeric: tabular-nums` wherever figures align in columns.

**Layout & spacing**
- Centered column, `max-width` ~860px (report) / ~940px (dashboard).
- Radius: 10px on cards/panels/header, 4–6px on inner elements (bars, images).
- Lay out groups with flex/grid + `gap`, not per-element margins.
- Wide content (tables, the Gantt SVG) sits in a panel with `overflow-x: auto`
  so the page never scrolls sideways.

**Components**
- **Header**: navy block, white title, muted subtitle line stating scope/date.
- **KPI row**: equal flex cards, big tabular number + small muted label.
- **Event card**: semantic tag pill, title (+ discount in green), brand·country
  line, summary, evidence in a `blockquote`, screenshot below.
- **Charts**: inline SVG only (no libraries, no external assets); faint
  gridlines, solid accent bars, values labeled.
- Print-friendly: `@media print` drops the page background and keeps borders,
  because these pages are routinely saved to PDF from the browser.

## Rules for any new visual output

1. Reuse the tokens above verbatim. Do not introduce a new hue; if you need
   another categorical color, take the next unused entry from the brand series
   palette.
2. Emit **self-contained** HTML — all CSS inline in a `<style>` block, images as
   relative paths or data URIs, SVG hand-built. No CDN links (they break offline
   and in email).
3. Match the existing structure: navy header → KPI row → titled panels. A new
   view should read as another page of the same report, not a different app.
4. Keep copy in French for client-facing output, and lead with the outcome.

## Note on theming

These reports deliberately commit to a single light theme: they are documents
meant to be read, printed, and turned into PDF, not an app UI that follows an OS
dark-mode toggle. That is a deliberate choice, not an omission — keep it light
unless the user explicitly asks for a dark variant, in which case redefine the
tokens (don't hardcode new colors inline).
