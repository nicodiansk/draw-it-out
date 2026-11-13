"""render.py: one test per refusal rule, exact code extraction, the CLI contract."""
import json
import tempfile
import unittest
from pathlib import Path

from helpers import render
import render as R


def piece(pid, shape="thing", **extra):
    return {"id": pid, "shape": shape, "label": pid.title(), "text": f"The {pid} step happens.", **extra}


class Base(unittest.TestCase):
    """A temp project root holding app.js with ten lines: 'line 1' … 'line 10'."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        (self.root / "app.js").write_text("".join(f"line {n}\n" for n in range(1, 11)), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def assertProblem(self, problems, field, words):
        hits = [p for p in problems if p.startswith(field + " →")]
        self.assertTrue(hits, f"no problem on {field}: {problems}")
        self.assertIn(words, hits[0])
        self.assertEqual(hits[0].count(" → "), 2, "field → problem → how to fix")


class Helpers(unittest.TestCase):
    def test_one_sentence(self):
        self.assertTrue(R.one_sentence("Version 1.5 is saved in pay.js."))
        self.assertTrue(R.one_sentence("Is the cart empty?"))
        self.assertFalse(R.one_sentence("The page loads. Then it saves."))
        self.assertFalse(R.one_sentence("It checks! Then it saves."))
        self.assertFalse(R.one_sentence("一。二。"))

    def test_parse_lines(self):
        self.assertEqual(R.parse_lines("12-30"), (12, 30))
        self.assertEqual(R.parse_lines("7"), (7, 7))
        for bad in ("12-3", "0-2", "a-b", ""):
            self.assertIsNone(R.parse_lines(bad), bad)

    def test_parse_focus(self):
        self.assertEqual(R.parse_focus("2,4-5"), [2, 4, 5])
        self.assertEqual(R.parse_focus(""), [])
        self.assertIsNone(R.parse_focus("x"))

    def test_find_cycle(self):
        pieces = [{"id": "a", "after": ["c"]}, {"id": "b", "after": ["a"]}, {"id": "c", "after": ["b"]}]
        self.assertEqual(R.find_cycle(pieces), ["a", "c", "b", "a"])
        self.assertEqual(R.find_cycle([{"id": "a", "after": ["a"]}]), ["a", "a"])
        self.assertIsNone(R.find_cycle([{"id": "a", "after": []}, {"id": "b", "after": ["a"]}]))

    def test_ranks_follow_after(self):
        pieces = [{"id": "a", "after": []}, {"id": "b", "after": ["a"]},
                  {"id": "c", "after": ["a", "b"]}, {"id": "d", "after": []}]
        self.assertEqual(R.ranks(pieces), {"a": 0, "b": 1, "c": 2, "d": 0})

    def test_title_lines(self):
        self.assertEqual(R.title_lines("What happens when I click Pay?"), ["What happens when", "I click Pay?"])
        self.assertEqual(R.title_lines("How does login work now"), ["How does login", "work now"])
        self.assertEqual(R.title_lines("a b c d e f g"), ["a b c", "d e", "f g"])
        self.assertEqual(R.title_lines("Login"), ["Login"])


class Extract(Base):
    def extract(self, code):
        problems = R.Problems()
        return R.extract(self.root, code, "pieces[0].code", problems), problems

    def test_lines_are_exact(self):
        (self.root / "x.py").write_text("a = 1\n\tb = '<\\/script>'\n  c = 3  \n", encoding="utf-8")
        code, problems = self.extract({"file": "x.py", "lines": "2-3", "focus": "3"})
        self.assertEqual(problems, [])
        self.assertEqual(code, {"file": "x.py", "start": 2, "end": 3,
                                "lines": ["\tb = '<\\/script>'", "  c = 3  "], "focus": [3]})

    def test_missing_file(self):
        code, problems = self.extract({"file": "nope.js", "lines": "1-2"})
        self.assertIsNone(code)
        self.assertProblem(problems, "pieces[0].code.file", "not found")

    def test_file_outside_root(self):
        for rel in ("../app.js", "/etc/hostname"):
            code, problems = self.extract({"file": rel, "lines": "1"})
            self.assertProblem(problems, "pieces[0].code.file", "not found")

    def test_lines_past_end_of_file(self):
        code, problems = self.extract({"file": "app.js", "lines": "8-12"})
        self.assertProblem(problems, "pieces[0].code.lines", "has 10 lines, asked for 8-12")

    def test_lines_not_a_range(self):
        code, problems = self.extract({"file": "app.js", "lines": "12-3"})
        self.assertProblem(problems, "pieces[0].code.lines", "not a line range")

    def test_focus_outside_range(self):
        code, problems = self.extract({"file": "app.js", "lines": "2-4", "focus": "5"})
        self.assertProblem(problems, "pieces[0].code.focus", "not inside 2-4")


if __name__ == "__main__":
    unittest.main()
