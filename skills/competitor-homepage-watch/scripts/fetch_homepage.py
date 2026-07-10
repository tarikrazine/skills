#!/usr/bin/env python3
"""fetch_homepage.py — [mutating] Fetch every configured homepage into today's snapshot dir.

Engine selection: uses the Firecrawl REST API (markdown + full-page screenshot)
when the FIRECRAWL_API_KEY environment variable is set; otherwise falls back to
plain HTTP with standard-library HTML-to-text extraction (no screenshot).

Writes <workspace>/snapshots/<date>/<brand>-<country>/{page.md,page.html,screenshot.png,meta.json}.
Per-target failures are recorded in meta.json and never abort the batch.

Exit codes: 0 = at least one target fetched, 2 = all targets failed, 1 = bad usage/config.
Python 3.8+, standard library only.
"""

import argparse
import base64
import datetime
import html
import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

FIRECRAWL_ENDPOINT = "https://api.firecrawl.dev/v2/scrape"
SCRAPFLY_ENDPOINT = "https://api.scrapfly.io/scrape"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
BLOCK_MARKERS = [
    "enable js", "enable javascript", "disable any ad blocker", "access denied",
    "captcha", "datadome", "verify you are human", "pardon our interruption",
    "attention required", "checking your browser",
]
SKIP_TAGS = {"script", "style", "noscript", "svg", "template", "iframe"}
BLOCK_TAGS = {
    "p", "div", "section", "article", "li", "h1", "h2", "h3", "h4", "h5", "h6",
    "header", "footer", "nav", "tr", "td", "th", "figcaption", "blockquote",
    "button", "option", "br",
}


class TextExtractor(HTMLParser):
    """Extract visible text blocks + image alt text from HTML (fallback engine)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._chunks = []
        self._current = []

    def _flush(self):
        text = " ".join("".join(self._current).split())
        if text:
            self._chunks.append(text)
        self._current = []

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag in BLOCK_TAGS:
            self._flush()
        if tag == "img":
            alt = dict(attrs).get("alt", "").strip()
            if alt:
                self._chunks.append(f"[image: {alt}]")

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return
        if tag in BLOCK_TAGS:
            self._flush()

    def handle_data(self, data):
        if not self._skip_depth:
            self._current.append(data)

    def get_text(self):
        self._flush()
        # De-duplicate consecutive identical chunks (menus repeat in mobile/desktop nav)
        out = []
        for chunk in self._chunks:
            if not out or out[-1] != chunk:
                out.append(chunk)
        return "\n\n".join(out)


def slugify(value):
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "target"


def http_get(url, timeout, headers=None, data=None, method=None):
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("User-Agent", USER_AGENT)
    req.add_header("Accept-Language", "*")
    for key, val in (headers or {}).items():
        req.add_header(key, val)
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        return resp.status, resp.read()


def fetch_via_firecrawl(url, api_key, timeout, extra_options=None):
    body = {
        "url": url,
        "formats": ["markdown", "html", {"type": "screenshot", "fullPage": True}],
        # "auto" escalates basic → enhanced proxies on request FAILURE only.
        # DataDome-class walls return HTTP 200 with a fake page, which auto
        # cannot see — fetch_target handles that by retrying with "enhanced".
        "proxy": "auto",
    }
    body.update(extra_options or {})
    payload = json.dumps(body).encode("utf-8")
    status, body = http_get(
        FIRECRAWL_ENDPOINT,
        timeout,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        data=payload,
        method="POST",
    )
    doc = json.loads(body.decode("utf-8", "replace"))
    if not doc.get("success"):
        raise RuntimeError(f"firecrawl error: {doc.get('error') or doc}")
    data = doc.get("data") or {}
    markdown = data.get("markdown") or ""
    raw_html = data.get("html") or ""
    screenshot = data.get("screenshot") or ""
    warning = doc.get("warning") or data.get("warning") or ""
    shot_bytes = None
    if screenshot.startswith("http"):
        try:
            _, shot_bytes = http_get(screenshot, timeout)
        except Exception:
            shot_bytes = None
    elif screenshot.startswith("data:image"):
        try:
            shot_bytes = base64.b64decode(screenshot.split(",", 1)[1])
        except Exception:
            shot_bytes = None
    return markdown, raw_html, shot_bytes, status, warning


def fetch_via_firecrawl_cli(url, timeout, extra_options=None):
    """Use the authenticated `firecrawl` CLI (no API key needed — it self-auths
    and auto-escalates its proxy on protected sites). Returns the same tuple as
    the REST path: (markdown, raw_html, shot_bytes, status, warning)."""
    fc = shutil.which("firecrawl")
    cmd = [fc, "scrape", url, "--format", "markdown,html,screenshot", "--json"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    out = (proc.stdout or "").strip()
    if not out:
        raise RuntimeError(f"firecrawl CLI: {(proc.stderr or 'no output').strip()[:200]}")
    try:
        doc = json.loads(out)
    except json.JSONDecodeError:
        s, e = out.find("{"), out.rfind("}")
        doc = json.loads(out[s:e + 1]) if s >= 0 and e > s else {}
    data = doc.get("data") or doc
    markdown = data.get("markdown") or ""
    raw_html = data.get("html") or data.get("rawHtml") or ""
    screenshot = data.get("screenshot") or ""
    meta = data.get("metadata") or {}
    status = meta.get("statusCode")
    warning = doc.get("warning") or data.get("warning") or ""
    shot_bytes = None
    if isinstance(screenshot, str) and screenshot.startswith("http"):
        try:
            _, shot_bytes = http_get(screenshot, timeout)
        except Exception:
            shot_bytes = None
    elif isinstance(screenshot, str) and screenshot.startswith("data:image"):
        try:
            shot_bytes = base64.b64decode(screenshot.split(",", 1)[1])
        except Exception:
            shot_bytes = None
    return markdown, raw_html, shot_bytes, status, warning


def fetch_via_http(url, timeout):
    status, body = http_get(url, timeout)
    raw_html = body.decode("utf-8", "replace")
    parser = TextExtractor()
    parser.feed(raw_html)
    text = html.unescape(parser.get_text())
    return text, raw_html, None, status


def fetch_via_scrapfly(url, api_key, timeout, country=None):
    """Web Unlocker path for DataDome / Cloudflare / PerimeterX–hardened sites.

    A single ScrapFly call with asp=true (Anti-Scraping Protection) + rendered JS
    returns the real homepage AND a full-page screenshot — the one method that
    beats the aggressive bot walls Firecrawl and headless browsers can't pass.
    Returns the same tuple as the other engines: (text, raw_html, shot, status, warning).
    """
    params = {
        "key": api_key,
        "url": url,
        "asp": "true",                 # bypass DataDome / Cloudflare / PerimeterX / etc.
        "render_js": "true",           # execute JS so the real homepage renders
        # The hard part is the SCREENSHOT: on sites like ATU the DataDome slider
        # is IP-dependent, so a plain render sometimes captures the challenge, not
        # the page. Two params make it reliable:
        #  - retry=true      → ScrapFly re-rolls the proxy/session on a failed ASP
        #                      solve until it lands on a good one (server-side).
        #  - wait_for_selector=nav → hold the render until the real homepage's
        #                      <nav> bar exists; the DataDome challenge page has
        #                      no <nav> (it DOES have a <footer>, so footer is not
        #                      a safe discriminator), so a challenged render never
        #                      "succeeds" and gets retried onto a clean proxy.
        # (timeout/rendering_wait can't be combined with retry — ScrapFly manages
        # its own budget when retry is on.)
        "retry": "true",
        "wait_for_selector": "nav",
        "auto_scroll": "true",         # scroll the page so lazy-loaded hero images render
        "screenshots[main]": "fullpage",  # full-page visual in the same call
        "screenshot_flags": "block_banners,high_quality",  # hide cookie/consent overlays
        "format": "raw",               # result.content = rendered HTML
    }
    if country:
        params["country"] = country
    endpoint = f"{SCRAPFLY_ENDPOINT}?{urllib.parse.urlencode(params)}"
    try:
        _, body = http_get(endpoint, timeout)
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", "replace")[:300]
        except Exception:
            pass
        raise RuntimeError(f"scrapfly HTTP {exc.code}: {detail}")
    doc = json.loads(body.decode("utf-8", "replace"))
    result = doc.get("result") or {}
    raw_html = result.get("content") or ""
    status = result.get("status_code")
    parser = TextExtractor()
    parser.feed(raw_html)
    text = html.unescape(parser.get_text())
    # Screenshot: result.screenshots[<name>].url is a ScrapFly URL that needs the
    # API key appended to download the image bytes.
    shot_bytes = None
    shots = result.get("screenshots") or {}
    if isinstance(shots, dict) and shots:
        first = next(iter(shots.values()))
        shot_url = first.get("url") if isinstance(first, dict) else None
        if shot_url:
            sep = "&" if "?" in shot_url else "?"
            try:
                _, shot_bytes = http_get(f"{shot_url}{sep}key={api_key}", timeout)
            except Exception:
                shot_bytes = None
    warning = "scrapfly returned a blocked-looking page" if looks_blocked(text) else ""
    return text, raw_html, shot_bytes, status, warning


def looks_blocked(content):
    head = content[:2000].lower()
    return len(content.strip()) < 400 or any(m in head for m in BLOCK_MARKERS)


def fetch_target(target, out_dir, api_key, timeout, firecrawl_defaults=None, scrapfly_key=None):
    slug = f"{slugify(target['brand'])}-{slugify(target['country'])}"
    target_dir = out_dir / slug
    target_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "brand": target["brand"],
        "country": target["country"],
        "url": target["url"],
        "own_brand": bool(target.get("own_brand", False)),
        "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "engine": "firecrawl" if api_key else ("firecrawl-cli" if shutil.which("firecrawl") else "http"),
        "status": None,
        "error": None,
        "has_screenshot": False,
        "screenshot_status": "none",
        "suspected_blocked": False,
        "needs_unlocker": False,
    }
    fc_cli = shutil.which("firecrawl")
    # ISO-2 country → ScrapFly proxy geolocation (Norauto FR → country=fr).
    cc = (target.get("country") or "").strip().lower()
    country = cc if re.fullmatch(r"[a-z]{2}", cc) else None
    # A target can pin the Web Unlocker explicitly; otherwise it is reached by
    # auto-escalation only when a bot wall is detected.
    force_unlocker = (
        target.get("engine") in ("web-unlocker", "scrapfly")
        or target.get("screenshot_engine") in ("web-unlocker", "scrapfly")
    )
    try:
        warning = ""
        if force_unlocker and scrapfly_key:
            # Hardened target pinned to the Web Unlocker: go straight to ScrapFly.
            meta["engine"] = "scrapfly(asp)"
            content, raw_html, shot, status, warning = fetch_via_scrapfly(target["url"], scrapfly_key, timeout, country)
        elif not api_key and fc_cli:
            # Preferred no-key path: the authenticated firecrawl CLI (self-auths,
            # auto-escalates proxy on protected sites).
            meta["engine"] = "firecrawl-cli"
            content, raw_html, shot, status, warning = fetch_via_firecrawl_cli(target["url"], timeout)
        elif api_key:
            options = dict(firecrawl_defaults or {})
            options.update(target.get("firecrawl") or {})
            content, raw_html, shot, status, warning = fetch_via_firecrawl(target["url"], api_key, timeout, options)
            # Bot walls (DataDome etc.) come back as HTTP 200 with a fake page,
            # so Firecrawl's own auto-escalation never triggers. Detect the wall
            # in the content and retry once with enhanced proxies (5 credits).
            if looks_blocked(content) and options.get("proxy") not in ("enhanced", "stealth"):
                options["proxy"] = "enhanced"
                content, raw_html, shot, status, warning = fetch_via_firecrawl(target["url"], api_key, timeout, options)
                meta["engine"] = "firecrawl(enhanced-retry)"
        else:
            content, raw_html, shot, status = fetch_via_http(target["url"], timeout)
        meta["status"] = status
        if not content.strip():
            raise RuntimeError("empty content extracted")
        meta["suspected_blocked"] = looks_blocked(content)

        # DEFAULT anti-bot behavior: if the page is still a wall (DataDome et al.)
        # and we haven't already used the Web Unlocker, escalate to ScrapFly's ASP
        # engine automatically. If no key is configured, flag needs_unlocker so the
        # skill can prompt a free (no-card) ScrapFly signup — exactly like Firecrawl.
        if meta["suspected_blocked"] and not meta["engine"].startswith("scrapfly"):
            if scrapfly_key:
                try:
                    u_txt, u_html, u_shot, u_status, u_warn = fetch_via_scrapfly(
                        target["url"], scrapfly_key, timeout, country)
                    if u_txt.strip() and not looks_blocked(u_txt):
                        content, raw_html, shot, status, warning = u_txt, u_html, u_shot, u_status, u_warn
                        meta["engine"] = "scrapfly(asp)[auto-escalated]"
                        meta["status"] = status
                        meta["suspected_blocked"] = False
                    else:
                        meta["unlocker_note"] = "scrapfly still returned a blocked page"
                except Exception as exc:  # noqa: BLE001
                    meta["unlocker_error"] = f"{type(exc).__name__}: {exc}"
            else:
                meta["needs_unlocker"] = True
        if force_unlocker and not scrapfly_key:
            meta["needs_unlocker"] = True

        (target_dir / "page.md").write_text(content, encoding="utf-8")
        if raw_html:
            (target_dir / "page.html").write_text(raw_html, encoding="utf-8")
        if shot:
            (target_dir / "screenshot.png").write_bytes(shot)
            meta["has_screenshot"] = True
            meta["screenshot_status"] = "captured"
        elif meta["engine"] == "http":
            meta["screenshot_status"] = "http-no-screenshot"  # plain HTTP fallback can't screenshot
        elif meta["needs_unlocker"]:
            # Hardened site, no Web Unlocker key yet: text may be partial, no visual.
            # The skill surfaces a one-time free ScrapFly setup prompt.
            meta["screenshot_status"] = "needs-web-unlocker"
        elif meta["suspected_blocked"] or "screenshot" in (warning or "").lower():
            # Bot-protected site the unlocker also couldn't crack this run. Content
            # may be partial; the visual isn't captured. Not a failure.
            meta["screenshot_status"] = "unsupported-on-protected-site"
            if warning:
                meta["firecrawl_warning"] = warning
        else:
            meta["screenshot_status"] = "missing"
        ok = True
    except Exception as exc:  # noqa: BLE001 — any per-target failure is recorded, batch continues
        meta["error"] = f"{type(exc).__name__}: {exc}"
        ok = False
    (target_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return slug, ok, meta


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", required=True, help="path to watch.config.json")
    ap.add_argument("--date", default=None, help="snapshot date YYYY-MM-DD (default: today)")
    ap.add_argument("--out", default=None, help="override snapshot dir (default: <workspace>/snapshots/<date>)")
    ap.add_argument("--only", default=None, help="only fetch targets whose slug contains this string")
    ap.add_argument("--timeout", type=int, default=90, help="per-request timeout in seconds")
    args = ap.parse_args()

    config_path = Path(args.config).expanduser().resolve()
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read config {config_path}: {exc}", file=sys.stderr)
        return 1
    targets = config.get("targets") or []
    if not targets:
        print("ERROR: config has no targets", file=sys.stderr)
        return 1
    for i, t in enumerate(targets):
        missing = [k for k in ("brand", "country", "url") if not t.get(k)]
        if missing:
            print(f"ERROR: target #{i} missing {missing}", file=sys.stderr)
            return 1

    date = args.date or datetime.date.today().isoformat()
    workspace = Path(config.get("workspace") or config_path.parent)
    if not workspace.is_absolute():
        workspace = (config_path.parent / workspace).resolve()
    out_dir = Path(args.out).expanduser().resolve() if args.out else workspace / "snapshots" / date
    out_dir.mkdir(parents=True, exist_ok=True)

    api_key = os.environ.get("FIRECRAWL_API_KEY", "").strip() or None
    scrapfly_key = os.environ.get("SCRAPFLY_API_KEY", "").strip() or None
    if api_key:
        engine_label = "firecrawl (REST, API key)"
    elif shutil.which("firecrawl"):
        engine_label = "firecrawl CLI (self-authenticated; screenshots on)"
    else:
        engine_label = "http-fallback (no firecrawl CLI or key; no screenshots, protected sites will 403)"
    unlocker_label = ("ScrapFly Web Unlocker ON (hardened sites like DataDome auto-escalate, +screenshot)"
                      if scrapfly_key else "Web Unlocker OFF (hardened sites will prompt a free ScrapFly setup)")
    print(f"engine: {engine_label}")
    print(f"unlocker: {unlocker_label}")
    print(f"snapshot dir: {out_dir}")

    successes = 0
    needs_unlocker = []
    for target in targets:
        slug = f"{slugify(target['brand'])}-{slugify(target['country'])}"
        if args.only and args.only not in slug:
            continue
        slug, ok, meta = fetch_target(
            target, out_dir, api_key, args.timeout, config.get("firecrawl"), scrapfly_key)
        if ok:
            successes += 1
            if meta["has_screenshot"]:
                shot = " +screenshot"
            elif meta["screenshot_status"] == "needs-web-unlocker":
                shot = " [needs Web Unlocker — see setup note below]"
            elif meta["screenshot_status"] == "unsupported-on-protected-site":
                shot = " [no screenshot — hardened site, unlocker couldn't capture this run]"
            else:
                shot = ""
            blocked = " [SUSPECTED BLOCKED — content looks like a bot wall]" if meta["suspected_blocked"] else ""
            if meta.get("needs_unlocker"):
                needs_unlocker.append(slug)
            print(f"OK   {slug} ({meta['engine']}{shot}){blocked}")
        else:
            print(f"FAIL {slug}: {meta['error']}")

    if needs_unlocker and not scrapfly_key:
        print()
        print("─" * 68)
        print("SETUP NEEDED — hardened (DataDome-class) sites detected:")
        print(f"  {', '.join(needs_unlocker)}")
        print("These competitors block every free engine. To capture their real")
        print("homepage + screenshot, the skill uses ScrapFly's Web Unlocker:")
        print("  1. Sign up FREE (no credit card): https://scrapfly.io/register")
        print("     → 1000 free API credits, enough to trial the watch.")
        print("  2. Copy your API key from the ScrapFly dashboard.")
        print("  3. Add it to your shell profile, then re-run the watch:")
        print("       echo 'export SCRAPFLY_API_KEY=\"...\"' >> ~/.zshrc && source ~/.zshrc")
        print("Once set, these sites auto-escalate through the unlocker — no per-")
        print("target config, it just works.")
        print("─" * 68)

    if successes == 0:
        print("ERROR: all targets failed", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
