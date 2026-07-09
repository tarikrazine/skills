#!/usr/bin/env python3
"""capture_visual.py — [mutating] Screenshot a bot-protected homepage via Browser Use.

Firecrawl's enhanced engine reads the TEXT of DataDome-class protected sites but
cannot screenshot them. Browser Use's hosted agent runs a hardened Chromium fork
with residential proxies + CAPTCHA solving, which can reach and screenshot those
pages. This script drives it over the Browser Use API: create a stealth session
with a residential proxy, run a screenshot task, download the produced image.

Auth, in order of preference (no manual key needed for the first):
  1. The `browser-use` CLI, which self-authenticates (agent signup / stored
     credentials) — nothing to configure. This is the default path.
  2. BROWSER_USE_API_KEY over raw REST, for headless/portable setups.

Only needed for targets Firecrawl can't screenshot. Costs a bit of Browser Use
credit + residential proxy bandwidth per capture (free tier covers light use).

Usage:
  capture_visual.py --url <url> --out <path.png> [--country fr] [--timeout 180]

Exit codes: 0 = screenshot saved, 2 = blocked / quota exhausted, 1 = bad usage/no engine.
Python 3.8+, standard library only (shells out to the browser-use CLI when present).
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REST_API = "https://api.browser-use.com/api/v2"


class BrowserUse:
    """Talks to the Browser Use API either through the auto-authenticating CLI
    (preferred: no key config) or raw REST with BROWSER_USE_API_KEY (fallback)."""

    def __init__(self):
        self.api_key = os.environ.get("BROWSER_USE_API_KEY", "").strip()
        self.cli = shutil.which("browser-use") or shutil.which("bu")
        self.mode = "cli" if (self.cli and not self.api_key) else ("rest" if self.api_key else ("cli" if self.cli else None))

    def call(self, method, path, body=None, timeout=45):
        if self.mode == "rest":
            return self._rest(method, path, body, timeout)
        return self._cli(method, path, body, timeout)

    def _rest(self, method, path, body, timeout):
        req = urllib.request.Request(REST_API + path,
                                     data=json.dumps(body).encode() if body is not None else None,
                                     method=method)
        req.add_header("Authorization", f"Bearer {self.api_key}")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        return json.loads(raw.decode("utf-8", "replace")) if raw else {}

    def _cli(self, method, path, body, timeout):
        # `browser-use cloud v2 <METHOD> </path> '<json>'` — the CLI injects auth.
        cmd = [self.cli, "cloud", "v2", method, path]
        if body is not None:
            cmd.append(json.dumps(body))
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = (proc.stdout or "").strip()
        if proc.returncode != 0 and not out:
            raise RuntimeError(f"browser-use CLI error: {(proc.stderr or '').strip()[:200]}")
        try:
            return json.loads(out) if out else {}
        except json.JSONDecodeError:
            # tolerate a JSON object embedded in human output
            start, end = out.find("{"), out.rfind("}")
            if start >= 0 and end > start:
                return json.loads(out[start:end + 1])
            raise


def download(url, dest, timeout=60):
    with urllib.request.urlopen(urllib.request.Request(url), timeout=timeout) as resp:
        dest.write_bytes(resp.read())


def _stop_session(bu, session_id):
    """Stop the task's browser session so it doesn't hold a concurrent slot.
    The free tier only allows a few concurrent sessions, so leaking them would
    make later captures fail with 'too many concurrent sessions'."""
    if not session_id:
        return
    try:
        bu.call("PATCH", f"/browsers/{session_id}", {"action": "stop"})
    except Exception:
        pass


def _classify_error(code, message):
    """Distinguish a concurrency limit (retry) from real credit exhaustion
    (add credit) from other errors. Returns the process exit code."""
    m = (message or "").lower()
    concurrent = "concurrent" in m or "too many active" in m or "too many concurrent" in m
    out_of_credit = ("credit" in m or "quota" in m or "insufficient" in m or code == 402)
    if concurrent:  # concurrency limit wins even if the message also says "upgrade"
        print("BUSY: Browser Use free tier hit its concurrent-session limit "
              "(HTTP 429). Wait for running captures to finish or space them out; "
              "no credit needed. Leaving this target text-only for now.", file=sys.stderr)
        return 2
    if out_of_credit or code == 429:
        print("QUOTA: Browser Use free capacity looks used up. Suggest adding "
              "credit to the account, or trim screenshot_engine to fewer targets. "
              "Continuing text-only.", file=sys.stderr)
        return 2
    print(f"ERROR: Browser Use ({code}): {message[:200]}", file=sys.stderr)
    return 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--url", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--country", default="fr")
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("--max-steps", type=int, default=6)
    args = ap.parse_args()

    bu = BrowserUse()
    if not bu.mode:
        print("ERROR: no Browser Use access — install the `browser-use` CLI "
              "(it self-authenticates) or set BROWSER_USE_API_KEY.", file=sys.stderr)
        return 1

    out = Path(args.out).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    task_prompt = (
        "Open the URL and wait for the real page to fully load, letting any "
        "'verifying'/anti-bot check resolve (scroll a little if needed). Then "
        "capture ONE full-page screenshot of the homepage and stop. Do not click "
        "into other pages."
    )
    try:
        # Let the agent create its own hardened-stealth session; steer the
        # residential proxy country via sessionSettings. (Pre-creating a browser
        # and passing sessionId is rejected as "Session not found".)
        task_body = {
            "task": task_prompt, "startUrl": args.url, "maxSteps": args.max_steps,
            "sessionSettings": {"proxyCountryCode": args.country},
        }
        try:
            task = bu.call("POST", "/tasks", task_body)
        except Exception:
            task_body.pop("sessionSettings", None)  # fall back to default proxy
            task = bu.call("POST", "/tasks", task_body)
        task_id = task.get("id")
        if not task_id:
            print(f"ERROR: task not created: {task}", file=sys.stderr)
            return 1

        deadline = time.time() + args.timeout
        detail, status = {}, ""
        while time.time() < deadline:
            time.sleep(6)
            detail = bu.call("GET", f"/tasks/{task_id}")
            status = (detail.get("status") or "").lower()
            if status in ("finished", "completed", "stopped", "failed", "error"):
                break

        files = detail.get("outputFiles") or detail.get("output_files") or []
        images = [f for f in files if str(f.get("fileName", "")).lower().endswith((".png", ".jpg", ".jpeg"))]
        pick = images[0] if images else (files[0] if files else None)
        if not pick:
            print(f"BLOCKED: agent produced no visual (status={status}); site likely still challenged.", file=sys.stderr)
            return 2

        signed = bu.call("GET", f"/files/tasks/{task_id}/output-files/{pick['id']}")
        dl = signed.get("url") or signed.get("downloadUrl")
        if not dl:
            print(f"ERROR: no download URL: {signed}", file=sys.stderr)
            return 2

        suffix = Path(pick["fileName"]).suffix.lower() or ".png"
        dest = out if suffix == out.suffix else out.with_suffix(suffix)
        download(dl, dest)
        print(f"saved: {dest} (browser-use {bu.mode}, cost≈${detail.get('cost')})")
        _stop_session(bu, detail.get("sessionId"))
        return 0
    except urllib.error.HTTPError as exc:
        return _classify_error(exc.code, exc.read().decode("utf-8", "replace")[:300])
    except subprocess.TimeoutExpired:
        print("ERROR: browser-use CLI timed out", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        return _classify_error(None, str(exc))


if __name__ == "__main__":
    sys.exit(main())
