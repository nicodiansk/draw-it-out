"""scripts/pack.sh builds the claude.ai zip with explain/ at its root."""
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

from helpers import REPO


class Pack(unittest.TestCase):
    def test_zip_holds_the_skill_and_nothing_else(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as copy:
            # Pack a copy of the repo holding a planted cache file, so the real repo stays clean.
            for part in ("scripts", "skills"):
                shutil.copytree(REPO / part, Path(copy) / part, ignore=shutil.ignore_patterns("__pycache__"))
            cache = Path(copy) / "skills/explain/engine/__pycache__"
            cache.mkdir()
            (cache / "x.pyc").write_bytes(b"x")
            res = subprocess.run(["bash", str(Path(copy) / "scripts/pack.sh"), tmp], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)
            zip_path = Path(res.stdout.strip())
            self.assertEqual(zip_path, Path(tmp).resolve() / "draw-it-out-explain.zip")
            names = zipfile.ZipFile(zip_path).namelist()
        for must in ("explain/SKILL.md", "explain/walk.md", "explain/sheet.md", "explain/schema.md",
                     "explain/engine/render.py", "explain/engine/template.html",
                     "explain/examples/walk.json", "explain/examples/sheet.json"):
            self.assertIn(must, names)
        self.assertTrue(all(n.startswith("explain/") for n in names), names)
        self.assertFalse([n for n in names if "capture.py" in n or "__pycache__" in n or n.endswith(".pyc")])


class Readme(unittest.TestCase):
    def test_readme_says_how_to_install_and_test(self):
        text = (REPO / "README.md").read_text(encoding="utf-8")
        for needle in ("claude plugin marketplace add nicodiansk/draw-it-out",
                       "claude plugin install draw-it-out@draw-it-out", "/draw-it-out:explain",
                       "bash scripts/pack.sh", "python3 -m unittest discover -s tests", "glitch-walk"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
