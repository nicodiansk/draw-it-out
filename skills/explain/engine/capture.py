#!/usr/bin/env python3
"""draw-it-out screenshots (Claude Code only, optional). Opens one localhost page, runs only the
declared clicks and waits, saves a PNG. Read-only: every request that is not a GET or HEAD to
localhost is blocked, so no form is sent, nothing is paid, no other site is opened. No JavaScript.

Usage: python3 capture.py http://localhost:3000/checkout --out shots/checkout.png \
         [--click "text=Pay"] [--wait 1500] [--wait "#receipt"]
Needs: pip install playwright && python3 -m playwright install chromium
"""
import argparse
import sys
from urllib.parse import urlsplit

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
MAX_WAIT_MS = 30000


def is_local(url):
    parts = urlsplit(url)
    return parts.scheme in ("http", "https") and parts.hostname in LOCAL_HOSTS


def allow_request(method, url):
    """The one network rule: read-only requests to this machine."""
    return method.upper() in ("GET", "HEAD") and is_local(url)


class Step(argparse.Action):
    """Keep --click and --wait in the order given."""

    def __call__(self, parser, namespace, value, option_string=None):
        kind = option_string.lstrip("-")
        if kind == "wait" and value.isdigit() and int(value) > MAX_WAIT_MS:
            parser.error(f"--wait {value}: at most {MAX_WAIT_MS} ms")
        steps = getattr(namespace, "steps", None) or []
        namespace.steps = steps + [(kind, value)]


def parse(argv):
    ap = argparse.ArgumentParser(description="Screenshot one localhost page after declared clicks and waits.")
    ap.add_argument("url")
    ap.add_argument("--out", required=True, help="PNG file to write")
    ap.add_argument("--click", action=Step, dest="steps", metavar="SELECTOR")
    ap.add_argument("--wait", action=Step, dest="steps", metavar="MS_OR_SELECTOR")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=800)
    args = ap.parse_args(argv)
    if not is_local(args.url):
        ap.error(f"{args.url}: only http(s)://localhost, 127.0.0.1 or [::1] pages can be opened")
    args.steps = args.steps or []
    return args


def main(argv=None):
    args = parse(argv)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright is not installed: pip install playwright && python3 -m playwright install chromium"
              " — or explain without screenshots.", file=sys.stderr)
        return 3
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception:
            browser = p.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": args.width, "height": args.height}, java_script_enabled=True)
        page.route("**/*", lambda route: route.continue_() if allow_request(route.request.method, route.request.url)
                   else route.abort())
        page.goto(args.url, wait_until="networkidle")
        for kind, value in args.steps:
            if kind == "click":
                page.click(value, timeout=MAX_WAIT_MS)
            elif value.isdigit():
                page.wait_for_timeout(int(value))
            else:
                page.wait_for_selector(value, timeout=MAX_WAIT_MS)
        page.screenshot(path=args.out)
        browser.close()
    print(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
