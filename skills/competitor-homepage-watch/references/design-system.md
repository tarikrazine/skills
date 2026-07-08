# Design system — visual output rules

Every visual artifact this skill produces (daily HTML report, monthly dashboard,
and any ad-hoc HTML view generated in analysis mode) MUST look like it came from
the same product: an **intelligence briefing** — the refined analyst-desk look of
a premium market-intelligence report. The bundled scripts (`render_report.py`,
`build_dashboard.py`) already encode these exact values. Read this before
modifying a script or generating any new visual, and reuse these tokens rather
than inventing a palette.

Why this matters: the model that runs this skill changes over time, and each
model has its own default aesthetic. Pinning the system here keeps every output
consistent, distinctive, and genuinely pleasant across model versions.

## The idea

A calm porcelain paper, deep petrol ink, and a single warm amber signal for
"new/alert" energy. The character comes from **type**: an editorial serif for
titles, a humanist sans for the body, and a monospace for every figure and date
(the "data" texture of an analyst's terminal). Not corporate navy-and-blue;
not the generic AI cream-serif-terracotta. Restraint everywhere, one confident
accent, precise details.

## Design tokens

**Palette**

| Token | Hex | Use |
|---|---|---|
| `--paper` | `#f6f7f5` | Page background — a cool porcelain neutral, chosen not defaulted |
| `--card` | `#ffffff` | Cards, panels, stat tiles |
| `--ink` | `#12211f` | Body text, masthead top rule (near-black, petrol bias) |
| `--petrol` | `#0f5f5c` | Primary accent: eyebrows, section markers, chart bars, brand #1 |
| `--amber` | `#c8792b` | Signal accent — the single "hot" highlight (new-operations KPI). Use sparingly |
| `--muted` | `#5c6b67` | Secondary text, labels |
| `--faint` | `#93a09b` | Footnotes, axis ticks, eyebrow-on-card |
| `--line` | `#dbe0dd` | Hairline borders, grid, dividers |

**Semantic colors** (event types — ink text on tint, plus a left card stripe;
never used as the main accent):

| Meaning | Ink | Tint | Stripe |
|---|---|---|---|
| New operation (`promo_start`) | `#1f7a5a` | `#e8f2ec` | `#1f7a5a` |
| Ended operation (`promo_end`) | `#a8452f` | `#f6eae5` | `#a8452f` |
| Modified operation (`promo_update`) | `#9a6a12` | `#f5eddb` | `#9a6a12` |
| Other change (`other_change`) | `#3d5350` | `#eaeeec` | `#3d5350` |
| Warning / issues panel | `#7a5c14` | `#fbf3e3`, border `#ecdcb4` |  |

**Brand series** (Gantt rows & brand chips, cycled by sorted brand+country so a
brand keeps its color): `#0f5f5c`, `#1f7a5a`, `#a8452f`, `#7a4fa0`, `#2c6b8a`,
`#9a6a12`, `#556b2f`, `#b0567a`.

**Typography** — three roles, all system stacks (no web fonts; the reports must
open offline):

| Role | Stack | Used for |
|---|---|---|
| Display serif | `"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif` | Masthead title, card titles, brand sub-heads |
| Body sans | `system-ui,-apple-system,"Segoe UI",Roboto,sans-serif` | Body text, labels, table cells |
| Mono | `ui-monospace,"SF Mono","Cascadia Code",Menlo,monospace` | KPI numbers, dates, discounts, meta lines, ticks |

Scale: masthead title 32–33px serif; card title 20px serif; KPI number 30px
mono; section `h2` 12px uppercase tracked sans; body 14px; eyebrow/label
10.5–11px uppercase, letter-spacing .14–.18em. Use `text-wrap: balance` on
serif headings and `font-variant-numeric: tabular-nums` on aligned figures.

**Layout & spacing**
- Narrow editorial measure: report ~760px, dashboard ~940px, centered.
- Masthead: 3px `--ink` top rule → petrol eyebrow → serif title → mono meta line
  above a hairline. This is the signature; every page opens with it.
- KPI row: a single rounded tile group with 1px `--line` gutters (grid, gap:1px
  on a `--line` background) — reads as one instrument panel, not four boxes.
- Section headings are quiet uppercase labels with a small petrol square marker
  and a hairline underline — structure without decoration.
- Radius 10–12px on cards/panels, 5–6px on inner elements.
- Wide content (tables, the Gantt SVG) lives in a `.panel` with
  `overflow-x: auto`; the page body never scrolls sideways.

**Components**
- **Event card**: left stripe in the semantic color, a small uppercase tag pill,
  a serif title with the discount as a mono chip, an uppercase faint brand·country
  line, a sentence of body, and the evidence as an *italic serif pull-quote*.
  Screenshot below, hairline-framed.
- **Gantt** (dashboard): weekend columns tinted with 4% petrol; Monday/1st day
  ticks in mono; bars rounded with a faint white top highlight for depth; a
  brand chip + label on the left; ongoing operations get a faded tail to signal
  "open-ended". Labels/discounts inside bars when they fit.
- **Charts**: inline hand-built SVG only — no libraries, no external assets.

**Print** — `@media print` drops the paper background, keeps hairlines, and
avoids breaking a heading from its content. These pages are routinely saved to
PDF from the browser, so they must print as cleanly as they display.

## Rules for any new visual output

1. Reuse the tokens above verbatim. Never introduce a new hue; for another
   categorical color, take the next unused entry from the brand series.
2. Emit **self-contained** HTML — CSS inline in one `<style>`, tokens as
   `:root` custom properties, images as relative paths or data URIs, SVG
   hand-built. No CDN links (they break offline and in email).
3. Open with the masthead (rule → eyebrow → serif title → mono meta) and keep
   the three type roles in their lanes (serif = titles, sans = body, mono =
   figures/dates). A new view must read as another page of the same briefing.
4. Spend boldness once — the amber signal and the serif titles carry the
   personality; keep everything around them quiet.
5. Client-facing copy follows the config `language` (`fr`/`en`/`es`) — the
   scripts pull every label from `scripts/i18n.py`, never hardcode UI text.
   Lead with the outcome.

## Note on theming

These reports deliberately commit to a single light theme: they are documents to
be read, printed, and turned into PDF, not an app UI that follows an OS dark
mode. That is a choice, not an omission — keep it light unless the user asks for
a dark variant, in which case redefine the `:root` tokens (never hardcode new
colors inline).
