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
import ssl
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

FIRECRAWL_ENDPOINT = "https://api.firecrawl.dev/v2/scrape"
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
    return markdown, raw_html, shot_bytes, status


def fetch_via_http(url, timeout):
    status, body = http_get(url, timeout)
    raw_html = body.decode("utf-8", "replace")
    parser = TextExtractor()
    parser.feed(raw_html)
    text = html.unescape(parser.get_text())
    return text, raw_html, None, status


def looks_blocked(content):
    head = content[:2000].lower()
    return len(content.strip()) < 400 or any(m in head for m in BLOCK_MARKERS)


def fetch_target(target, out_dir, api_key, timeout, firecrawl_defaults=None):
    slug = f"{slugify(target['brand'])}-{slugify(target['country'])}"
    target_dir = out_dir / slug
    target_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "brand": target["brand"],
        "country": target["country"],
        "url": target["url"],
        "own_brand": bool(target.get("own_brand", False)),
        "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "engine": "firecrawl" if api_key else "http",
        "status": None,
        "error": None,
        "has_screenshot": False,
        "suspected_blocked": False,
    }
    try:
        if api_key:
            options = dict(firecrawl_defaults or {})
            options.update(target.get("firecrawl") or {})
            content, raw_html, shot, status = fetch_via_firecrawl(target["url"], api_key, timeout, options)
            # Bot walls (DataDome etc.) come back as HTTP 200 with a fake page,
            # so Firecrawl's own auto-escalation never triggers. Detect the wall
            # in the content and retry once with enhanced proxies (5 credits).
            if looks_blocked(content) and options.get("proxy") not in ("enhanced", "stealth"):
                options["proxy"] = "enhanced"
                content, raw_html, shot, status = fetch_via_firecrawl(target["url"], api_key, timeout, options)
                meta["engine"] = "firecrawl(enhanced-retry)"
        else:
            content, raw_html, shot, status = fetch_via_http(target["url"], timeout)
        meta["status"] = status
        if not content.strip():
            raise RuntimeError("empty content extracted")
        meta["suspected_blocked"] = looks_blocked(content)
        (target_dir / "page.md").write_text(content, encoding="utf-8")
        if raw_html:
            (target_dir / "page.html").write_text(raw_html, encoding="utf-8")
        if shot:
            (target_dir / "screenshot.png").write_bytes(shot)
            meta["has_screenshot"] = True
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
    print(f"engine: {'firecrawl' if api_key else 'http-fallback (no FIRECRAWL_API_KEY; no screenshots)'}")
    print(f"snapshot dir: {out_dir}")

    successes = 0
    for target in targets:
        slug = f"{slugify(target['brand'])}-{slugify(target['country'])}"
        if args.only and args.only not in slug:
            continue
        slug, ok, meta = fetch_target(target, out_dir, api_key, args.timeout, config.get("firecrawl"))
        if ok:
            successes += 1
            shot = " +screenshot" if meta["has_screenshot"] else ""
            blocked = " [SUSPECTED BLOCKED — content looks like a bot wall; try firecrawl proxy=stealth]" if meta["suspected_blocked"] else ""
            print(f"OK   {slug} ({meta['engine']}{shot}){blocked}")
        else:
            print(f"FAIL {slug}: {meta['error']}")
    if successes == 0:
        print("ERROR: all targets failed", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
