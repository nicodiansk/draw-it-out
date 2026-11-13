"""The skill's markdown stays in step with render.py."""
import re
import unittest

from helpers import REPO
import render as R

SKILL = REPO / "skills" / "explain"


class SkillEntry(unittest.TestCase):
    def test_frontmatter(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        front = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        self.assertIsNotNone(front)
        self.assertRegex(front.group(1), r"(?m)^name: explain$")
        self.assertRegex(front.group(1), r"(?m)^description: .{40,}")

    def test_routes_to_mode_files_and_renderer(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        for name in ("walk.md", "sheet.md", "schema.md", "engine/render.py", "--root", "unsure"):
            self.assertIn(name, text)
        self.assertIn("at most three times", text)


class ModeFiles(unittest.TestCase):
    def test_modes_ask_at_most_three_questions(self):
        for name in ("walk.md", "sheet.md"):
            text = (SKILL / name).read_text(encoding="utf-8")
            self.assertIn("at most three questions", text, name)
            for shape in R.SHAPES:
                self.assertIn(f"`{shape}`", text, f"{name} maps {shape}")

    def test_walk_uses_capture_safely(self):
        text = (SKILL / "walk.md").read_text(encoding="utf-8")
        self.assertIn("engine/capture.py", text)
        self.assertIn("Never ask the user to sign in", text)
        self.assertIn("Only files you opened", text)


if __name__ == "__main__":
    unittest.main()
