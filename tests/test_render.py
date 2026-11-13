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
        self.assertTrue(R.one_sentence("It reads a file, e.g. the cart, and saves it."))
        self.assertFalse(R.one_sentence("It saves. 2 rows change."))

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

    def test_existing_file_above_root_is_refused(self):
        (self.root / "secret.txt").write_text("token\n", encoding="utf-8")
        sub = self.root / "project"
        sub.mkdir()
        (sub / "link.txt").symlink_to(self.root / "secret.txt")
        for rel in ("../secret.txt", "link.txt"):
            problems = R.Problems()
            self.assertIsNone(R.extract(sub, {"file": rel, "lines": "1"}, "pieces[0].code", problems), rel)
            self.assertProblem(problems, "pieces[0].code.file", "not found")

    def test_only_newlines_split_lines(self):
        (self.root / "odd.py").write_text("a = 1\n\x0c\nb = 2\nc = 'x\u2028y'\nd = 4\n", encoding="utf-8")
        code, problems = self.extract({"file": "odd.py", "lines": "3-5"})
        self.assertEqual(problems, [])
        self.assertEqual(code["lines"], ["b = 2", "c = 'x\u2028y'", "d = 4"])
        code, problems = self.extract({"file": "odd.py", "lines": "6"})
        self.assertProblem(problems, "pieces[0].code.lines", "has 5 lines")

    def test_huge_focus_range_is_refused_without_expanding(self):
        code, problems = self.extract({"file": "app.js", "lines": "2-4", "focus": "1-99999999999"})
        self.assertProblem(problems, "pieces[0].code.focus", "not inside 2-4")

    def test_lines_past_end_of_file(self):
        code, problems = self.extract({"file": "app.js", "lines": "8-12"})
        self.assertProblem(problems, "pieces[0].code.lines", "has 10 lines, asked for 8-12")

    def test_lines_not_a_range(self):
        code, problems = self.extract({"file": "app.js", "lines": "12-3"})
        self.assertProblem(problems, "pieces[0].code.lines", "not a line range")

    def test_focus_outside_range(self):
        code, problems = self.extract({"file": "app.js", "lines": "2-4", "focus": "5"})
        self.assertProblem(problems, "pieces[0].code.focus", "not inside 2-4")


class Sheet(Base):
    def check(self, pieces, **extra):
        problems = R.Problems()
        sheet = R.check_sheet({"pieces": pieces, **extra}, None, set(), self.root, problems, [])
        return sheet, problems

    def test_valid_sheet_has_ranks_and_columns(self):
        sheet, problems = self.check([piece("a"), piece("b", after=["a"])],
                                     unsure=[{"after": "b", "text": "I didn't see the email leave."}])
        self.assertEqual(problems, [])
        self.assertEqual([(p["id"], p["rank"], p["n"]) for p in sheet["pieces"]], [("a", 0, 1), ("b", 1, 2)])
        self.assertEqual(sheet["unsure"][0]["rank"], 2)
        self.assertEqual(sheet["cols"], 3)

    def test_shape_outside_vocabulary(self):
        _, problems = self.check([piece("a", shape="cloud")])
        self.assertProblem(problems, "pieces[0].shape", "not a shape")

    def test_text_longer_than_one_sentence(self):
        _, problems = self.check([piece("a", text="The page loads. Then it saves.")])
        self.assertProblem(problems, "pieces[0].text", "longer than one sentence")

    def test_more_than_twenty_pieces(self):
        many = [piece(f"p{n}") for n in range(21)]
        _, problems = self.check(many)
        self.assertProblem(problems, "pieces", "21 pieces, the limit is 20")
        self.assertEqual(self.check(many[:20])[1], [])

    def test_after_cycle(self):
        _, problems = self.check([piece("a", after=["c"]), piece("b", after=["a"]), piece("c", after=["b"])])
        self.assertProblem(problems, "pieces[].after", "cycle: a > c > b > a")

    def test_unknown_after_id(self):
        _, problems = self.check([piece("a", after=["zz"])])
        self.assertProblem(problems, "pieces[0].after", "\"zz\" is not a piece")

    def test_duplicate_id(self):
        _, problems = self.check([piece("a"), piece("a")])
        self.assertProblem(problems, "pieces[1].id", "used twice")

    def test_label_over_three_words(self):
        p = piece("a")
        p["label"] = "One two three four"
        self.assertProblem(self.check([p])[1], "pieces[0].label", "longer than three words")

    def test_error_arrow_must_go_back(self):
        pieces = [piece("a"), piece("b", after=["a"])]
        _, problems = self.check(pieces, arrows=[{"from": "a", "to": "b", "label": "Fails"}])
        self.assertProblem(problems, "arrows[0]", "does not come before")
        sheet, problems = self.check(pieces, arrows=[{"from": "b", "to": "a", "label": "Fails"}])
        self.assertEqual(problems, [])
        self.assertEqual(sheet["arrows"], [{"from": "b", "to": "a", "label": "Fails"}])

    def test_malformed_arrows_unsure_and_after_are_refused(self):
        sheet, problems = self.check([piece("a"), piece("b", after=[["a"]])])
        self.assertProblem(problems, "pieces[1].after", "not a piece on this sheet")
        sheet, problems = self.check([piece("a"), piece("b", after=["a"])], arrows=["b>a"], unsure="gap")
        self.assertProblem(problems, "arrows[0]", "not an object")
        self.assertProblem(problems, "unsure", "not a list")

    def test_code_is_extracted(self):
        sheet, problems = self.check([piece("a", code={"file": "app.js", "lines": "2-3"})])
        self.assertEqual(sheet["pieces"][0]["code"]["lines"], ["line 2", "line 3"])


class Build(Base):
    def doc(self, pieces=None, **over):
        base = {"mode": "walk", "title": "What happens when I click Pay?", "lang": "en",
                "pieces": pieces if pieces is not None else [piece("a"), piece("b", after=["a"])]}
        base.update(over)
        return base

    def problems(self, doc):
        return R.build(doc, self.root)[1]

    def test_valid_doc_passes(self):
        data, problems = R.build(self.doc(), self.root)
        self.assertEqual(problems, [])
        self.assertEqual(data["title"], ["What happens when", "I click Pay?"])
        self.assertEqual(data["ui"]["sheet"], "Sheet")
        self.assertEqual(len(data["sheets"]), 1)

    def test_mode(self):
        self.assertProblem(self.problems(self.doc(mode="tour")), "mode", "not a mode")

    def test_title_over_nine_words(self):
        d = self.doc(title="one two three four five six seven eight nine ten")
        self.assertProblem(self.problems(d), "title", "nine words")

    def test_language_without_builtin_words_needs_ui(self):
        self.assertProblem(self.problems(self.doc(lang="de")), "ui", "missing: sheet")
        ui = {k: k.upper() for k in R.UI_KEYS}
        self.assertEqual(self.problems(self.doc(lang="de", ui=ui)), [])

    def test_italian_is_built_in(self):
        data, problems = R.build(self.doc(lang="it"), self.root)
        self.assertEqual(data["ui"]["sheet"], "Tavola")

    def test_unknown_ui_key(self):
        self.assertProblem(self.problems(self.doc(ui={"colour": "x"})), "ui", "unknown keys: colour")

    def test_sheets_and_pieces_together(self):
        d = self.doc(sheets=[{"pieces": [piece("x")]}])
        self.assertProblem(self.problems(d), "sheets", "both")

    def test_several_sheets_need_names_and_count_per_sheet(self):
        twelve = lambda tag: [piece(f"{tag}{n}") for n in range(12)]
        d = self.doc(sheets=[{"name": "One", "pieces": twelve("a")}, {"pieces": twelve("b")}])
        del d["pieces"]
        self.assertProblem(self.problems(d), "sheets[1].name", "missing")
        d["sheets"][1]["name"] = "Two"
        data, problems = R.build(d, self.root)
        self.assertEqual(problems, [])
        self.assertEqual(data["sheets"][1]["pieces"][0]["n"], 13)

    def test_after_cannot_cross_sheets(self):
        d = self.doc(sheets=[{"name": "One", "pieces": [piece("a")]},
                             {"name": "Two", "pieces": [piece("b", after=["a"])]}])
        del d["pieces"]
        self.assertProblem(self.problems(d), "sheets[1].pieces[0].after", "not a piece on this sheet")

    def test_ids_unique_across_sheets(self):
        d = self.doc(sheets=[{"name": "One", "pieces": [piece("a")]}, {"name": "Two", "pieces": [piece("a")]}])
        del d["pieces"]
        self.assertProblem(self.problems(d), "sheets[1].pieces[0].id", "used twice")

    def test_ui_values_must_be_words(self):
        ui = {k: k.upper() for k in R.UI_KEYS}
        ui["replay"] = ""
        self.assertProblem(self.problems(self.doc(lang="de", ui=ui)), "ui.replay", "empty")
        self.assertProblem(self.problems(self.doc(ui=["x"])), "ui", "not an object")

    def test_malformed_sheets_and_shots_are_refused(self):
        d = self.doc(sheets=["one"])
        del d["pieces"]
        self.assertProblem(self.problems(d), "sheets[0]", "not an object")
        self.assertProblem(self.problems(self.doc(shots=["a.png"])), "shots[0]", "not an object")
        self.assertProblem(self.problems(self.doc(shots={"file": "a.png"})), "shots", "not a list")

    def test_top_level_arrows_next_to_sheets(self):
        d = self.doc(sheets=[{"name": "One", "pieces": [piece("a")]}], unsure=[{"after": "a", "text": "Gap."}])
        del d["pieces"]
        self.assertProblem(self.problems(d), "unsure", "inside each sheet")

    def test_sheet_name_and_shot_tag_are_short(self):
        d = self.doc(sheets=[{"name": "One two three four", "pieces": [piece("a")]}])
        del d["pieces"]
        self.assertProblem(self.problems(d), "sheets[0].name", "three words")
        (self.root / "s.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")
        d = self.doc(shots=[{"file": "s.svg", "piece": "a", "tag": "one two three four five six seven"}])
        self.assertProblem(self.problems(d), "shots[0].tag", "six words")

    def test_shot_must_exist(self):
        d = self.doc(shots=[{"file": "missing.png", "piece": "a", "tag": "The button"}])
        self.assertProblem(self.problems(d), "shots[0].file", "not found")

    def test_shot_is_embedded_from_shots_dir(self):
        side = self.root / "side"
        side.mkdir()
        (side / "s.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")
        d = self.doc(shots=[{"file": "s.svg", "piece": "a", "tag": "The page"}])
        self.assertProblem(self.problems(d), "shots[0].file", "not found")
        data, problems = R.build(d, self.root, side)
        self.assertEqual(problems, [])
        self.assertTrue(data["shots"][0]["src"].startswith("data:image/svg+xml;base64,"))


class Cli(Base):
    def doc(self, pieces=None, **over):
        base = {"mode": "walk", "title": "What happens when I click Pay?", "lang": "en",
                "pieces": pieces or [piece("a"), piece("b", after=["a"])]}
        base.update(over)
        return base

    def write(self, doc, folder=None):
        path = (folder or self.root) / "doc.json"
        path.write_text(json.dumps(doc), encoding="utf-8")
        return path

    def test_refusal_exits_1_and_lists_every_problem(self):
        d = self.doc([piece("a", shape="cloud", text="One. Two.")])
        res = render(self.write(d), self.root / "out.html", root=self.root)
        self.assertEqual(res.returncode, 1)
        self.assertIn("pieces[0].shape →", res.stderr)
        self.assertIn("pieces[0].text →", res.stderr)
        self.assertFalse((self.root / "out.html").exists())

    def test_success_writes_html_with_data(self):
        res = render(self.write(self.doc()), self.root / "out.html", root=self.root)
        self.assertEqual(res.returncode, 0, res.stderr)
        html = (self.root / "out.html").read_text(encoding="utf-8")
        self.assertIn('<html lang="en">', html)
        self.assertIn("<title>What happens when I click Pay?</title>", html)
        self.assertNotIn("__DATA__", html)
        self.assertIn('"label": "A"', html)

    def test_text_cannot_close_the_script_tag(self):
        p = piece("a", text="It prints </script><script>alert(1)</script> on screen.")
        d = self.doc([p], title="__DATA__ </title> test")
        res = render(self.write(d), self.root / "out.html", root=self.root)
        self.assertEqual(res.returncode, 0, res.stderr)
        html = (self.root / "out.html").read_text(encoding="utf-8")
        self.assertEqual(html.count("</script>"), 2)
        self.assertEqual(html.count("<script"), 2)
        payload = html.split('type="application/json">', 1)[1].split("</script>", 1)[0]
        self.assertEqual(json.loads(payload)["sheets"][0]["pieces"][0]["text"], p["text"])
        self.assertIn("<title>__DATA__ &lt;/title&gt; test</title>", html)

    def test_shots_resolve_next_to_the_json(self):
        side = self.root / "side"
        side.mkdir()
        (side / "s.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")
        path = self.write(self.doc(shots=[{"file": "s.svg", "piece": "a", "tag": "The page"}]), side)
        res = render(path, self.root / "out.html", root=self.root)
        self.assertEqual(res.returncode, 0, res.stderr)

    def test_bad_json_exits_1(self):
        path = self.root / "bad.json"
        path.write_text("{", encoding="utf-8")
        res = render(path, self.root / "out.html", root=self.root)
        self.assertEqual(res.returncode, 1)
        self.assertIn("write valid JSON", res.stderr)


if __name__ == "__main__":
    unittest.main()
