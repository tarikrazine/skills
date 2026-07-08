# watch.config.json — schema and rules

The config lives at the root of the watch workspace. All paths in the workspace
are derived from it.

## Fields

| Field | Type | Required | Meaning |
|---|---|---|---|
| `workspace` | string | no | Data directory. Relative paths resolve against the config file's directory. Default: the config file's directory. |
| `language_hint` | string | no | Primary language of the monitored sites (e.g. `"fr"`). Helps the agent read promo wording; has no effect on scripts. |
| `targets` | array | yes | One entry per brand × country homepage. |
| `targets[].brand` | string | yes | Brand name as it should appear in reports and the calendar (e.g. `"BrandA"`). |
| `targets[].country` | string | yes | ISO-ish country code (`"FR"`, `"DE"`, `"ES"`…). Brand+country must be unique — the pair becomes the target slug. |
| `targets[].url` | string | yes | The exact homepage URL to snapshot, with scheme. Prefer the final URL after redirects (avoid `http://` → `https://` hops and country-picker interstitials). |
| `targets[].own_brand` | boolean | no | `true` for the user's own sites. Own-brand pages get the same treatment; the flag lets reports and analyses separate "us" vs "them". Default `false`. |
| `firecrawl` | object | no | Extra options merged into every Firecrawl scrape request (e.g. `{"waitFor": 3000}`). Ignored by the HTTP fallback. |
| `targets[].firecrawl` | object | no | Per-target Firecrawl options, merged over the global ones. The important one: `{"proxy": "enhanced"}` for sites behind aggressive bot protection (DataDome and similar; Firecrawl formerly called this proxy tier "stealth"). Enhanced costs ~5 credits/scrape vs 1. The fetch script also auto-retries with enhanced when it detects a bot wall in the response, so this option mainly saves the wasted first attempt on known-protected sites. |

## Annotated example

```json
{
  "workspace": ".",
  "language_hint": "fr",
  "targets": [
    { "brand": "BrandA",  "country": "FR", "url": "https://www.branda.example/",    "own_brand": false },
    { "brand": "BrandA",  "country": "ES", "url": "https://www.branda.example/es/", "own_brand": false },
    { "brand": "BrandB",  "country": "FR", "url": "https://www.brandb.example/",    "own_brand": false,
      "firecrawl": { "proxy": "enhanced" } },
    { "brand": "MyBrand", "country": "FR", "url": "https://www.mybrand.example/",   "own_brand": true }
  ]
}
```

## Validation rules

- Every target needs non-empty `brand`, `country`, `url` — `fetch_homepage.py` refuses the whole config otherwise (fail fast beats silently skipping a competitor).
- Duplicate brand+country pairs overwrite each other's snapshots. If a brand runs two distinct sites in one country, disambiguate the country field (`"FR-pro"`, `"FR-b2c"`).
- Homepage only, by design: the homepage is where retailers surface their current commercial operations. Deep category/promo pages change too often and drown the signal. If the user insists on an extra page, add it as its own target with a distinct country suffix (`"FR-promos"`).

## Changing the config over time

Adding a target is safe any time — its first day reports `new_target`. Removing a
target stops future snapshots but keeps its history in the calendar. Renaming a
brand breaks the link with its history (the slug changes); prefer keeping the
original spelling.
