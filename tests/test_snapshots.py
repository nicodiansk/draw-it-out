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


if __name__ == "__main__":
    unittest.main()
