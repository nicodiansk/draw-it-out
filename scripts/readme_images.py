#!/usr/bin/env python3
"""Rebuild the README images in docs/readme/ (needs Playwright, Chromium or Chrome, and Pillow).

  python3 scripts/readme_images.py

hero.jpg          the banner (docs/readme/hero.html), 1280x640, also the GitHub social preview
how-it-works.jpg  draw-it-out explaining itself (docs/readme/how-it-works.json, rendered by render.py)
walk.jpg          the bundled walk example, fully built
sheet.jpg         the bundled Italian sheet example, fully built
"""
import subprocess
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "docs" / "readme"
ENGINE = REPO / "skills" / "explain" / "engine"
EXAMPLES = REPO / "skills" / "explain" / "examples"


def render(json_path, root, out):
    subprocess.run([sys.executable, str(ENGINE / "render.py"), str(json_path), "--root", str(root),
                    "--out", str(out)], check=True, capture_output=True)


def save_jpeg(png, out):
    """Film grain makes lossless PNGs 2-6 MB; a progressive JPEG keeps it at a few hundred KB."""
    from PIL import Image
    Image.open(png).convert("RGB").save(out, quality=85, optimize=True, progressive=True)
    png.unlink()


def shoot(browser, url, out, width, height=900, full=False, scale=2):
    page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=scale,
                            reduced_motion="reduce")
    page.goto(url, wait_until="networkidle")
    page.evaluate("document.fonts.ready")
    page.wait_for_timeout(300)
    if full:
        # A viewport as tall as the page, not full_page: the page's grain layer is position: fixed
        # and would only cover the first screen.
        page.set_viewport_size({"width": width, "height": page.evaluate("document.documentElement.scrollHeight")})
        page.wait_for_timeout(300)
    png = out.with_suffix(".png")
    page.screenshot(path=str(png))
    save_jpeg(png, out)
    page.close()
    print(out.relative_to(REPO))


def main():
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as p:
        tmp = Path(tmp)
        try:
            browser = p.chromium.launch()
        except Exception:  # no bundled Chromium: use the system Chrome
            browser = p.chromium.launch(channel="chrome")
        render(OUT / "how-it-works.json", REPO, tmp / "how.html")
        render(EXAMPLES / "walk.json", EXAMPLES, tmp / "walk.html")
        render(EXAMPLES / "sheet.json", EXAMPLES, tmp / "sheet.html")
        shoot(browser, (OUT / "hero.html").as_uri(), OUT / "hero.jpg", 1280, 640)
        shoot(browser, (tmp / "how.html").as_uri(), OUT / "how-it-works.jpg", 1280, full=True)
        shoot(browser, (tmp / "walk.html").as_uri(), OUT / "walk.jpg", 1280, full=True)
        shoot(browser, (tmp / "sheet.html").as_uri(), OUT / "sheet.jpg", 1280, full=True)
        browser.close()


if __name__ == "__main__":
    main()
