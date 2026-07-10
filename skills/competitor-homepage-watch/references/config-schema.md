# watch.config.json — schema and rules

The config lives at the root of the watch workspace. All paths in the workspace
are derived from it.

## Fields

| Field | Type | Required | Meaning |
|---|---|---|---|
| `workspace` | string | no | Data directory. Relative paths resolve against the config file's directory. Default: the config file's directory. |
| `language` | string | no | **Output language of the HTML report and dashboard**: `"fr"`, `"en"`, or `"es"`. Falls back to `language_hint`, then French. Ask the user for this at setup — it's the language their reports are written in, independent of the languages of the sites they watch. |
| `language_hint` | string | no | Primary language of the monitored sites (e.g. `"fr"`). Helps the agent read promo wording; used as the report-language fallback when `language` is unset. |
| `targets` | array | yes | One entry per brand × country homepage. |
| `targets[].brand` | string | yes | Brand name as it should appear in reports and the calendar (e.g. `"BrandA"`). |
| `targets[].country` | string | yes | ISO-ish country code (`"FR"`, `"DE"`, `"ES"`…). Brand+country must be unique — the pair becomes the target slug. |
| `targets[].url` | string | yes | The exact homepage URL to snapshot, with scheme. Prefer the final URL after redirects (avoid `http://` → `https://` hops and country-picker interstitials). |
| `targets[].own_brand` | boolean | no | `true` for the user's own sites. Own-brand pages get the same treatment; the flag lets reports and analyses separate "us" vs "them". Default `false`. |
| `targets[].engine` | string | no | Force this target's fetch engine. The one value that matters: `"web-unlocker"` (alias `"scrapfly"`) pins a **known DataDome/Cloudflare-hardened** competitor (Norauto, Midas, ATU…) straight to the ScrapFly Web Unlocker, skipping the wasted Firecrawl attempt. The unlocker returns the real page **and** a full-page screenshot in one call. Needs `SCRAPFLY_API_KEY` in the environment (free signup, no card, at `scrapfly.io/register`). If you don't set this, hardened sites are still handled — the fetch **auto-escalates** to the unlocker the moment it detects a bot wall — so `engine` is purely an optimization for sites you already know are protected. |
| `firecrawl` | object | no | Extra options merged into every Firecrawl scrape request (e.g. `{"waitFor": 3000}`). Ignored by the HTTP fallback. |
| `targets[].firecrawl` | object | no | Per-target Firecrawl options, merged over the global ones. `{"proxy": "enhanced"}` bumps Firecrawl's proxy tier for moderately-protected sites (Firecrawl formerly called this "stealth"; ~5 credits/scrape vs 1). Note: enhanced does **not** beat the hardest DataDome configs — for those use `"engine": "web-unlocker"` (above). |
| `targets[].screenshot_engine` | string | no | Legacy per-target visual override: `"browser-use"` routes only the screenshot through Browser Use's stealth agent. Superseded by `engine: "web-unlocker"`, which is more reliable on DataDome-class sites (Browser Use's CAPTCHA solver does not beat the hardest ones) and returns text + screenshot together. Kept for back-compat. |
| `screenshot_proxy_country` | string | no | Residential proxy country code for the Browser Use screenshot engine (default `"fr"`). The Web Unlocker instead derives its proxy country from each target's `country` field automatically. |

## Environment (no secrets in this file)

The config never holds API keys. Engines read them from the environment:

| Env var | For | How to get it |
|---|---|---|
| `FIRECRAWL_API_KEY` | Firecrawl REST fallback (the `firecrawl` CLI self-authenticates and needs no key) | firecrawl.dev → API Keys |
| `SCRAPFLY_API_KEY` | **Web Unlocker for DataDome-hardened sites** | **Free, no credit card: https://scrapfly.io/register → 1000 credits.** The fetch prints a setup note the first time a hardened site is detected without this key. |
| `BROWSER_USE_API_KEY` | Legacy Browser Use screenshot engine (its CLI also self-authenticates) | browser-use.com |

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
