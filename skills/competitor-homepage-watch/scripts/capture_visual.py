#!/usr/bin/env python3
"""capture_visual.py — [mutating] Screenshot a bot-protected homepage via Browser Use.

Firecrawl's enhanced engine reads the TEXT of DataDome-class protected sites but
cannot screenshot them. Browser Use's hosted agent runs a hardened Chromium fork
with residential proxies + CAPTCHA solving, which can reach and screenshot those
pages. This script drives it over pure REST (no browser dependency): create an
agent task, poll to completion, download the produced image into the snapshot.

Only needed for targets Firecrawl can't screenshot (screenshot_status =
unsupported-on-protected-site). Requires BROWSER_USE_API_KEY. Costs a few cents
per capture (agent step + residential proxy bandwidth).

Usage:
  capture_visual.py --url <url> --out <path.png> [--country fr] [--timeout 180]

Exit codes: 0 = screenshot saved, 2 = captured nothing / blocked, 1 = bad usage/no key.
Python 3.8+, standard library only.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.browser-use.com/api/v2"


def api_call(method, path, api_key, body=None, timeout=30):
    url = API + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return json.loads(raw.decode("utf-8", "replace")) if raw else {}


def download(url, dest, timeout=60):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        dest.write_bytes(resp.read())


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--url", required=True)
    ap.add_argument("--out", required=True, help="destination image path (.png)")
    ap.add_argument("--country", default="fr", help="residential proxy country code")
    ap.add_argument("--timeout", type=int, default=180, help="max seconds to wait for the agent")
    ap.add_argument("--max-steps", type=int, default=6)
    args = ap.parse_args()

    api_key = os.environ.get("BROWSER_USE_API_KEY", "").strip()
    if not api_key:
        print("ERROR: BROWSER_USE_API_KEY not set — cannot capture protected-site visual", file=sys.stderr)
        return 1

    out = Path(args.out).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    task_prompt = (
        "Open the URL and wait for the real page to fully load, letting any "
        "'verifying'/anti-bot check resolve (scroll a little if needed). Then take "
        "exactly ONE full-page screenshot of the homepage and stop. Do not click "
        "into other pages."
    )
    try:
        session = api_call("POST", "/browsers", api_key,
                           {"proxyCountryCode": args.country, "timeout": max(60, args.timeout)})
        session_id = session.get("id")
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: could not provision stealth browser: {exc}", file=sys.stderr)
        return 1

    try:
        task = api_call("POST", "/tasks", api_key, {
            "task": task_prompt,
            "startUrl": args.url,
            "maxSteps": args.max_steps,
            "sessionId": session_id,
        })
        task_id = task.get("id")
        if not task_id:
            print(f"ERROR: task not created: {task}", file=sys.stderr)
            return 1

        deadline = time.time() + args.timeout
        status, detail = "", {}
        while time.time() < deadline:
            time.sleep(6)
            detail = api_call("GET", f"/tasks/{task_id}", api_key)
            status = (detail.get("status") or "").lower()
            if status in ("finished", "completed", "stopped", "failed", "error"):
                break

        files = detail.get("outputFiles") or detail.get("output_files") or []
        images = [f for f in files if str(f.get("fileName", "")).lower().endswith((".png", ".jpg", ".jpeg"))]
        pick = images[0] if images else (files[0] if files else None)
        if not pick:
            print(f"BLOCKED: agent produced no visual (status={status}). Site likely still challenged.", file=sys.stderr)
            return 2

        fid = pick["id"]
        signed = api_call("GET", f"/files/tasks/{task_id}/output-files/{fid}", api_key)
        dl = signed.get("url") or signed.get("downloadUrl")
        if not dl:
            print(f"ERROR: no download URL for output file: {signed}", file=sys.stderr)
            return 2

        suffix = Path(pick["fileName"]).suffix.lower() or ".png"
        tmp = out.with_suffix(suffix)
        download(dl, tmp)
        if suffix != out.suffix:
            # Agent saved a PDF/other; keep it next to the expected path and note it.
            print(f"saved: {tmp} (agent produced {suffix}; not a PNG)")
        else:
            print(f"saved: {out} (browser-use stealth, cost≈${detail.get('cost')})")
        return 0
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:200]
        if exc.code in (402, 429):
            print("QUOTA: Browser Use free capacity looks used up "
                  f"(HTTP {exc.code}). Suggest adding credit to the account, or "
                  "trim screenshot_engine to fewer targets. Continuing text-only.",
                  file=sys.stderr)
            return 2
        print(f"ERROR: browser-use API {exc.code}: {detail}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        if session_id:
            try:
                api_call("DELETE", f"/browsers/{session_id}", api_key)
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
