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


if __name__ == "__main__":
    unittest.main()
