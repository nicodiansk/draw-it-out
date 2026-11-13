"""The two examples render, and their HTML matches the snapshots.
After a deliberate template change: UPDATE_SNAPSHOTS=1, rerun, review the diff, commit."""
import os
import tempfile
import unittest
from pathlib import Path

from helpers import EXAMPLES, REPO, render

SNAPSHOTS = REPO / "tests" / "snapshots"


def rendered(name):
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / f"{name}.html"
        res = render(EXAMPLES / f"{name}.json", out)
        return res, out.read_text(encoding="utf-8") if out.exists() else ""


class Examples(unittest.TestCase):
    def test_both_examples_render(self):
        for name in ("walk", "sheet"):
            res, html = rendered(name)
            self.assertEqual(res.returncode, 0, f"{name}: {res.stderr}")
            self.assertIn("dio-data", html)

    def test_walk_example_uses_every_feature(self):
        res, html = rendered("walk")
        for needle in ('"shape": "ai"', '"shape": "tested"', '"arrows": [{', '"unsure": [{', "data:image/svg+xml;base64,"):
            self.assertIn(needle, html)


class Snapshots(unittest.TestCase):
    def check(self, name):
        res, html = rendered(name)
        self.assertEqual(res.returncode, 0, res.stderr)
        snap = SNAPSHOTS / f"{name}.html"
        if os.environ.get("UPDATE_SNAPSHOTS") == "1" or not snap.exists():
            SNAPSHOTS.mkdir(exist_ok=True)
            snap.write_text(html, encoding="utf-8")
            self.fail(f"snapshot written to {snap}: review it, then rerun without UPDATE_SNAPSHOTS")
        self.assertEqual(html, snap.read_text(encoding="utf-8"), f"{name}.html differs from {snap}")

    def test_walk(self):
        self.check("walk")

    def test_sheet(self):
        self.check("sheet")


if __name__ == "__main__":
    unittest.main()
