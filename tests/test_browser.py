"""Browser smoke test: renders the examples and opens them in Chromium.
Skips when Playwright or a browser is missing (pip install playwright && python3 -m playwright install chromium)."""
import json
import tempfile
import unittest
from pathlib import Path

from helpers import EXAMPLES, render

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


def launch(p):
    try:
        return p.chromium.launch()
    except Exception:
        return p.chromium.launch(channel="chrome")


@unittest.skipIf(sync_playwright is None, "playwright not installed")
class BrowserSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.pages = {}
        for name in ("walk", "sheet"):
            out = Path(cls.tmp.name) / f"{name}.html"
            render(EXAMPLES / f"{name}.json", out)
            doc = json.loads((EXAMPLES / f"{name}.json").read_text(encoding="utf-8"))
            sheets = doc.get("sheets", [doc])
            cls.pages[name] = (out.as_uri(), sum(len(s["pieces"]) for s in sheets))
        cls.pw = sync_playwright().start()
        try:
            cls.browser = launch(cls.pw)
        except Exception as err:
            cls.pw.stop()
            raise unittest.SkipTest(f"no browser: {err}")

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.tmp.cleanup()

    def open(self, name, width=1280, motion="no-preference"):
        page = self.browser.new_page(viewport={"width": width, "height": 900}, reduced_motion=motion)
        page.route("http*://**", lambda route: route.abort())
        page.goto(self.pages[name][0])
        return page

    def test_piece_count_matches_json(self):
        for name, (_, count) in self.pages.items():
            page = self.open(name, motion="reduce")
            self.assertEqual(page.locator(".dio-piece").count(), count, name)
            page.close()

    def test_reduced_motion_shows_everything_at_once(self):
        for name in self.pages:
            page = self.open(name, motion="reduce")
            total = page.locator(".dio-step").count()
            self.assertEqual(page.locator(".dio-step.is-on").count(), total, name)
            page.close()

    def test_build_starts_empty_with_motion(self):
        page = self.open("walk")
        total = page.locator(".dio-step").count()
        self.assertLess(page.locator(".dio-step.is-on").count(), total)
        page.wait_for_function(f"document.querySelectorAll('.dio-step.is-on').length === {total}", timeout=total * 500 + 3000)
        page.close()

    def test_no_horizontal_scroll_at_390(self):
        for name in self.pages:
            page = self.open(name, width=390, motion="reduce")
            width = page.evaluate("document.documentElement.scrollWidth")
            self.assertLessEqual(width, 390, name)
            page.close()

    def test_tap_opens_code_panel_with_extracted_lines(self):
        page = self.open("walk", motion="reduce")
        page.locator(".dio-piece[data-id=cart] button").click()
        panel = page.locator(".dio-code").first
        self.assertTrue(panel.is_visible())
        self.assertIn("shop/api/pay.js:8-11", panel.inner_text())
        self.assertEqual(page.locator(".dio-line").count(), 4)
        self.assertEqual(page.locator(".dio-line.is-focus").count(), 1)
        page.close()

    def test_build_follows_story_order(self):
        page = self.open("walk", motion="reduce")
        steps = page.evaluate("""() => Array.from(document.querySelectorAll('.dio-piece'))
            .map(e => [e.dataset.id, +e.getAttribute('data-step')])""")
        order = [pid for pid, _ in sorted(steps, key=lambda x: x[1])]
        self.assertEqual(order, ["click", "request", "cart", "card", "save", "note", "done"])
        back = page.evaluate("+document.querySelector('.dio-backs-svg g').getAttribute('data-step')")
        self.assertLess(back, dict(steps)["save"])
        self.assertGreater(back, dict(steps)["card"])
        page.keyboard.press("ArrowLeft")
        self.assertFalse(page.locator(".dio-piece[data-id=done]").evaluate("e => e.classList.contains('is-on')"))
        self.assertTrue(page.locator(".dio-backs-svg g").evaluate("e => e.classList.contains('is-on')"))
        page.close()

    def test_column_arrow_appears_with_its_piece(self):
        page = self.open("walk", motion="reduce")
        same = page.evaluate("""() => Array.from(document.querySelectorAll('.dio-slot')).slice(1).every(slot =>
            slot.querySelector('.dio-join').getAttribute('data-step') ===
            slot.querySelector('.dio-col > .dio-step').getAttribute('data-step'))""")
        self.assertTrue(same)
        page.close()

    def test_wrapped_rows_start_with_an_arrow(self):
        page = self.open("walk", width=1280, motion="reduce")
        rows = page.evaluate("""() => {
            const rows = {};
            document.querySelectorAll('.dio-slot').forEach((slot, i) => {
                const top = Math.round(slot.getBoundingClientRect().top);
                (rows[top] = rows[top] || []).push(slot.firstElementChild.classList[0]);
            });
            return Object.keys(rows).sort((a, b) => a - b).map(k => rows[k]);
        }""")
        self.assertGreater(len(rows), 1, "the walk should wrap at 1280px")
        for row in rows[1:]:
            self.assertEqual(row[0], "dio-join", rows)
        page.close()

    def test_error_path_is_an_arrow_back_to_its_target(self):
        for width in (1280, 900, 390):
            page = self.open("walk", width=width, motion="reduce")
            d = page.locator(".dio-backs-svg path").first.get_attribute("d")
            self.assertGreaterEqual(d.count("L"), 3, (width, d))
            tip = page.locator(".dio-backs-svg path.dio-head").first.bounding_box()
            target = page.locator(".dio-piece[data-id=click]").bounding_box()
            cx, cy = tip["x"] + tip["width"] / 2, tip["y"] + tip["height"] / 2
            self.assertTrue(target["x"] - 4 <= cx <= target["x"] + target["width"] + 24, (width, tip, target))
            self.assertTrue(target["y"] - 4 <= cy <= target["y"] + target["height"] + 24, (width, tip, target))
            page.close()

    def test_shot_tag_never_covers_the_screenshot(self):
        for width in (1280, 390):
            page = self.open("walk", width=width, motion="reduce")
            tag = page.locator(".dio-tag").first.bounding_box()
            img = page.locator(".dio-shot img").first.bounding_box()
            self.assertLessEqual(tag["y"] + tag["height"], img["y"] + 1, width)
            page.close()


if __name__ == "__main__":
    unittest.main()
