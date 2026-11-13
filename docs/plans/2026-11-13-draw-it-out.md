# draw-it-out Implementation Plan

**Goal:** Ship the `draw-it-out` Claude Code plugin (and its claude.ai skill zip): one `explain` skill with two modes, walk and sheet, that turns a JSON the model writes into one self-contained HTML sheet that builds itself in the Zine look.
**Architecture:** The model writes only data; `skills/explain/engine/render.py` (stdlib) validates it, reads every code snippet from disk, and injects the result into `engine/template.html`, whose inline JS draws the sheet (columns ranked by `after`, stop-motion build-in, code panel, shots strip, legend, StageBar). `capture.py` is an optional, read-only Playwright screenshotter for localhost; `SKILL.md` routes to `walk.md` or `sheet.md` plus `schema.md`; `scripts/pack.sh` zips `skills/explain/` for claude.ai.
**Tech Stack:** Python 3 standard library (`unittest`, `argparse`, `json`), vanilla HTML/CSS/JS, optional Playwright for Python (screenshots and browser tests), bash + `zip`.

All commands run from the repo root, `/home/user/draw-it-out`. Every code block below was run in this order in a scratch copy: each task's test failed before its code and passed after, and the full suite passes: 63 tests, of which the 6 browser tests skip without Playwright.

## Lanes
| Lane | Owns files | Tasks | After | Executor | Effort |
|------|-----------|-------|-------|----------|--------|
| scaffold | `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.gitignore`, `LICENSE`, `tests/helpers.py`, `tests/test_manifest.py` | 1 | — | inline | — |
| engine | `skills/explain/engine/render.py`, `skills/explain/engine/template.html`, `skills/explain/examples/walk.json`, `skills/explain/examples/sheet.json`, `skills/explain/examples/shop/app/pay-button.js`, `skills/explain/examples/shop/api/pay.js`, `skills/explain/examples/shop/lib/db.js`, `skills/explain/examples/shop/lib/card.js`, `skills/explain/examples/shop/tests/db.test.js`, `skills/explain/examples/shop/shots/checkout.svg`, `tests/test_render.py`, `tests/test_snapshots.py`, `tests/snapshots/walk.html`, `tests/snapshots/sheet.html`, `tests/test_browser.py` | 2–9 | scaffold | builder | medium |
| capture | `skills/explain/engine/capture.py`, `tests/test_capture.py` | 10 | scaffold | builder | low |
| skill | `skills/explain/SKILL.md`, `skills/explain/walk.md`, `skills/explain/sheet.md`, `skills/explain/schema.md`, `tests/test_skill_docs.py` | 11–13 | engine | inline | — |
| pack | `scripts/pack.sh`, `tests/test_pack.py`, `README.md` | 14–15 | engine, capture, skill | inline | — |

## Review Focus
- A piece's text containing `</script>`, or a title containing `__DATA__` → shown as plain text; the page still has exactly its two script blocks (pinned: Task 6)
- A code path that climbs out of `--root` (`../app.js`, `/etc/hostname`) → refused as not found, never read (pinned: Task 3)
- A sentence with a decimal or a file name ("Version 1.5 is saved in pay.js.") → still one sentence, not refused (pinned: Task 2)
- A language with no built-in words (`"lang": "de"`) → refused until `ui` holds every key translated, so the page never falls back to English chrome silently (pinned: Task 5)
- A declared click on a Pay/submit button during capture → the screenshot is taken and no POST reaches the local server (pinned: Task 10)

## Decisions beyond the design
- Each piece has an `id` (for `after`, arrows, shots) and a 1–3 word `label` drawn on the shape; `text` is the one-sentence claim under it (the Zine Diagram kit puts 1–2 word labels on shapes and full sentences on cards).
- `arrows[]` holds only the error path (dashed pink, `to` must rank before `from`). Flow arrows come from `after` and are drawn between columns.
- More than 20 pieces: `sheets[]` (each with `name`) replaces top-level `pieces`/`arrows`/`unsure`; `after` and arrows stay inside one sheet; ids are unique across sheets; piece numbers run on across sheets.
- `title` is at most nine words, split into 2–3 lines of at most three words.
- `en` and `it` UI words are built in; any other `lang` must bring a full `ui` object (the sheet is in the asker's language, chrome included).
- Code paths resolve under `--root` (the project); screenshot paths resolve next to the JSON, because the project is read-only and shots are written beside the JSON.
- `capture.py` allows only GET/HEAD requests to localhost: forms and API POSTs are blocked, external assets don't load. It falls back to a system Chrome (`channel="chrome"`) when Playwright's own Chromium is missing.
- Doodles are three inline SVGs copied path for path from the Zine design system's Doodles group: asterisk-pink, sparkle-paper, cross-paper. The other seven (dots, scribble, the other colour of each) aren't used in v1.
- At desktop, columns are 200px and wrap onto new rows; under 700px they stack top to bottom.
- The claude.ai zip leaves out `capture.py` (Claude Code only). No `NOTICE`: nothing is copied from glitch-walk; the README credits it.


### Task 1: Plugin manifests and test scaffold

**Lane:** scaffold

**Files:**
- Create: `tests/helpers.py`
- Create: `tests/test_manifest.py`
- Create: `.claude-plugin/plugin.json`
- Create: `.claude-plugin/marketplace.json`
- Create: `.gitignore`
- Create: `LICENSE`

**Step 1: Write the failing test**

`tests/helpers.py` is shared by every test file (paths, and `render()` runs `render.py` as the skill does):

```python
"""Shared paths and helpers for the renderer tests."""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ENGINE = REPO / "skills" / "explain" / "engine"
EXAMPLES = REPO / "skills" / "explain" / "examples"
sys.path.insert(0, str(ENGINE))


def render(json_path, out, root=EXAMPLES):
    """Run render.py as the skill does; return the CompletedProcess."""
    return subprocess.run([sys.executable, str(ENGINE / "render.py"), str(json_path),
                           "--root", str(root), "--out", str(out)],
                          capture_output=True, text=True)
```

`tests/test_manifest.py`:

```python
"""Plugin and marketplace manifests."""
import json
import unittest

from helpers import REPO

PLUGIN = REPO / ".claude-plugin" / "plugin.json"
MARKET = REPO / ".claude-plugin" / "marketplace.json"


class Manifest(unittest.TestCase):
    def test_plugin_name_and_version(self):
        plugin = json.loads(PLUGIN.read_text(encoding="utf-8"))
        self.assertEqual(plugin["name"], "draw-it-out")
        self.assertRegex(plugin["version"], r"^\d+\.\d+\.\d+$")
        self.assertEqual(plugin["license"], "MIT")

    def test_marketplace_lists_this_repo_without_a_version(self):
        market = json.loads(MARKET.read_text(encoding="utf-8"))
        self.assertEqual(market["name"], "draw-it-out")
        [entry] = market["plugins"]
        self.assertEqual((entry["name"], entry["source"]), ("draw-it-out", "./"))
        self.assertNotIn("version", entry)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**
Run: `python3 -m unittest discover -s tests -p test_manifest.py -v`
Expected: FAIL: 2 errors, `FileNotFoundError` for `.claude-plugin/plugin.json` and `marketplace.json`

**Step 3: Write minimal implementation**

`.claude-plugin/plugin.json`:

```json
{
  "name": "draw-it-out",
  "displayName": "Draw It Out",
  "description": "Explains your code or a process as a drawing that builds itself, in plain words. One skill, two modes: walk (follow a click through your code) and sheet (draw a process).",
  "version": "0.1.0",
  "author": {
    "name": "Nicholas"
  },
  "homepage": "https://github.com/nicodiansk/draw-it-out",
  "repository": "https://github.com/nicodiansk/draw-it-out",
  "license": "MIT",
  "keywords": ["explain", "diagram", "walkthrough", "visual", "onboarding"]
}
```

`.claude-plugin/marketplace.json` (no `version`: it lives only in plugin.json):

```json
{
  "name": "draw-it-out",
  "owner": {
    "name": "Nicholas"
  },
  "metadata": {
    "description": "Explanations drawn as sheets that build themselves"
  },
  "plugins": [
    {
      "name": "draw-it-out",
      "source": "./",
      "description": "Explains your code or a process as a drawing that builds itself, in plain words.",
      "strict": true
    }
  ]
}
```

`.gitignore`:

```
dist/
__pycache__/
*.pyc
```

`LICENSE`: the standard MIT text, holder line `Copyright (c) 2026 Nicholas Previtali`:

```
MIT License

Copyright (c) 2026 Nicholas Previtali

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

**Step 4: Run test to verify it passes**
Run: `python3 -m unittest discover -s tests -p test_manifest.py -v`
Expected: PASS, 2 tests OK

**Step 5: Commit**
`git add -A && git commit -m "feat: plugin manifests and test scaffold"`


### Task 2: render.py: pure helpers (sentences, line ranges, order, title)

**Lane:** engine

**Files:**
- Create: `skills/explain/engine/render.py`
- Create: `tests/test_render.py`

**Step 1: Write the failing test**

`tests/test_render.py` (later tasks add classes above the `__main__` block; `Base` and `piece` are used from Task 3 on):

```python
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


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**
Run: `python3 -m unittest discover -s tests -p test_render.py -v`
Expected: FAIL: `ModuleNotFoundError: No module named 'render'`

**Step 3: Write minimal implementation**

`skills/explain/engine/render.py` (constants, UI words and the pure helpers; later tasks append to the end of this file):

```python
#!/usr/bin/env python3
"""draw-it-out renderer: validate a walk or sheet JSON, read the code it names from disk,
write one self-contained HTML file. Standard library only.

Usage: python3 render.py walk.json --root /path/to/project --out walk.html
Exit 0: written. Exit 1: refused, one line per problem on stderr: field → problem → how to fix.
"""
import argparse
import base64
import html
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SHAPES = ("you", "ai", "check", "thing", "tested", "look")
MAX_PIECES = 20
MAX_TITLE_WORDS = 9
MAX_LABEL_WORDS = 3
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
LINES_RE = re.compile(r"^(\d+)(?:-(\d+))?$")
LANG_RE = re.compile(r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$")
SENTENCE_END = re.compile(r"[.!?]+\s+|[。！？]+")
SHOT_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
              ".webp": "image/webp", ".gif": "image/gif", ".svg": "image/svg+xml"}
UI = {
    "en": {"sheet": "Sheet", "legend": "Legend", "replay": "Replay", "prev": "Back",
           "next": "Next", "see": "What you see", "close": "Close", "back_to": "back to",
           "you": "You: a click, a command, a wait",
           "ai": "AI call: a different answer each time",
           "check": "Check: the same answer every time",
           "thing": "A thing: a file, a request, a saved row",
           "tested": "Covered by tests", "error": "Error path: back one step",
           "look": "Look here: the result that matters",
           "unsure": "Not sure: something I didn't see"},
    "it": {"sheet": "Tavola", "legend": "Legenda", "replay": "Rivedi", "prev": "Indietro",
           "next": "Avanti", "see": "Quello che vedi", "close": "Chiudi",
           "back_to": "torna a",
           "you": "Tu: un clic, un comando, un'attesa",
           "ai": "Chiamata AI: ogni volta una risposta diversa",
           "check": "Controllo: sempre la stessa risposta",
           "thing": "Una cosa: un file, una richiesta, una riga salvata",
           "tested": "Coperto da test", "error": "Errore: torna indietro di un passo",
           "look": "Guarda qui: il risultato che conta",
           "unsure": "Non sono sicuro: qualcosa che non ho visto"},
}
UI_KEYS = tuple(UI["en"])


class Problems(list):
    def add(self, field, problem, fix):
        self.append(f"{field} → {problem} → {fix}")


def one_sentence(text):
    """True when text holds at most one sentence: no sentence end followed by more text."""
    parts = [p for p in SENTENCE_END.split(text.strip()) if p.strip()]
    return len(parts) <= 1


def parse_lines(spec):
    """'12-30' → (12, 30); '7' → (7, 7); anything else → None."""
    m = LINES_RE.match(str(spec).strip())
    if not m:
        return None
    start = int(m.group(1))
    end = int(m.group(2) or start)
    return (start, end) if 1 <= start <= end else None


def parse_focus(spec):
    """'14,20-22' → [14, 20, 21, 22]; '' → []; bad → None."""
    out = []
    for part in [p for p in str(spec).split(",") if p.strip()]:
        rng = parse_lines(part)
        if rng is None:
            return None
        out.extend(range(rng[0], rng[1] + 1))
    return out


def find_cycle(pieces):
    """Return the ids of one `after` cycle, in order, or None."""
    after = {p["id"]: p.get("after", []) for p in pieces}
    state = {}

    def visit(node, trail):
        state[node] = "open"
        for nxt in after.get(node, []):
            if state.get(nxt) == "open":
                return trail[trail.index(nxt):] + [nxt]
            if nxt in after and nxt not in state:
                found = visit(nxt, trail + [nxt])
                if found:
                    return found
        state[node] = "done"
        return None

    for pid in after:
        if pid not in state:
            found = visit(pid, [pid])
            if found:
                return found
    return None


def ranks(pieces):
    """Column of each piece: 0 with no `after`, else 1 + the highest column it comes after."""
    after = {p["id"]: p.get("after", []) for p in pieces}
    memo = {}

    def rank(pid):
        if pid not in memo:
            memo[pid] = 1 + max((rank(a) for a in after[pid]), default=-1)
        return memo[pid]

    return {pid: rank(pid) for pid in after}


def title_lines(title):
    """Split the title into 2-3 lines of at most three words (one line for a single word)."""
    words = title.split()
    count = 1 if len(words) < 2 else max(2, math.ceil(len(words) / 3))
    size, extra = divmod(len(words), count)
    lines, i = [], 0
    for n in range(count):
        step = size + (1 if n < extra else 0)
        lines.append(" ".join(words[i:i + step]))
        i += step
    return lines
```

**Step 4: Run test to verify it passes**
Run: `python3 -m unittest discover -s tests -p test_render.py -v`
Expected: PASS, 6 tests OK

**Step 5: Commit**
`git add -A && git commit -m "feat(engine): render.py helpers for sentences, line ranges, order and title"`


### Task 3: render.py: read code from disk, exactly

**Lane:** engine

**Files:**
- Modify: `skills/explain/engine/render.py` (append)
- Modify: `tests/test_render.py`

**Step 1: Write the failing test**

Insert above the final `if __name__ == "__main__":` block of `tests/test_render.py`:

```python
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
```

**Step 2: Run test to verify it fails**
Run: `python3 -m unittest discover -s tests -p test_render.py -v`
Expected: FAIL: 6 errors, `AttributeError: module 'render' has no attribute 'extract'`

**Step 3: Write minimal implementation**

Append to the end of `skills/explain/engine/render.py`:

```python
def inside(root, rel):
    """Resolve rel under root; None when it is absolute or escapes root."""
    if Path(rel).is_absolute():
        return None
    path = (root / rel).resolve()
    return path if path == root or root in path.parents else None


def extract(root, code, field, problems):
    """Read code.lines of code.file under root, exactly as on disk."""
    if not isinstance(code, dict) or not isinstance(code.get("file"), str):
        problems.add(field, "needs {\"file\": ..., \"lines\": ...}",
                     "give the file path relative to --root and a line range like \"12-30\"")
        return None
    rel = code["file"]
    path = inside(root, rel)
    if path is None or not path.is_file():
        problems.add(f"{field}.file", f"file {rel} not found under {root}",
                     "use a path relative to --root of a file you opened")
        return None
    rng = parse_lines(code.get("lines", ""))
    if rng is None:
        problems.add(f"{field}.lines", f"\"{code.get('lines')}\" is not a line range",
                     "write it as \"12-30\" or \"12\"")
        return None
    text = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if rng[1] > len(text):
        problems.add(f"{field}.lines", f"{rel} has {len(text)} lines, asked for {rng[0]}-{rng[1]}",
                     f"pick lines inside 1-{len(text)}")
        return None
    focus = parse_focus(code.get("focus", ""))
    if focus is None or any(n < rng[0] or n > rng[1] for n in focus):
        problems.add(f"{field}.focus", f"\"{code.get('focus')}\" is not inside {rng[0]}-{rng[1]}",
                     "list key lines like \"14,20-22\" inside the range, or leave focus out")
        return None
    return {"file": rel, "start": rng[0], "end": rng[1],
            "lines": text[rng[0] - 1:rng[1]], "focus": focus}
```

**Step 4: Run test to verify it passes**
Run: `python3 -m unittest discover -s tests -p test_render.py -v`
Expected: PASS, 12 tests OK

**Step 5: Commit**
`git add -A && git commit -m "feat(engine): extract code lines from disk, refuse missing files and ranges"`


### Task 4: render.py: check one sheet (shapes, sentences, limit, cycles, arrows, gaps)

**Lane:** engine

**Files:**
- Modify: `skills/explain/engine/render.py` (append)
- Modify: `tests/test_render.py`

**Step 1: Write the failing test**

Insert above the final `if __name__ == "__main__":` block of `tests/test_render.py`:

```python
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

    def test_code_is_extracted(self):
        sheet, problems = self.check([piece("a", code={"file": "app.js", "lines": "2-3"})])
        self.assertEqual(sheet["pieces"][0]["code"]["lines"], ["line 2", "line 3"])
```

**Step 2: Run test to verify it fails**
Run: `python3 -m unittest discover -s tests -p test_render.py -v`
Expected: FAIL: 10 errors, `AttributeError: module 'render' has no attribute 'check_sheet'`

**Step 3: Write minimal implementation**

Append to the end of `skills/explain/engine/render.py`:

```python
def check_text(value, field, problems, sentence=True):
    if not isinstance(value, str) or not value.strip():
        problems.add(field, "missing", "write one plain sentence")
        return False
    if sentence and not one_sentence(value):
        problems.add(field, "longer than one sentence", "keep one sentence; move the rest to another piece")
        return False
    return True


def check_sheet(sheet, si, ids, root, problems, numbered):
    where = f"sheets[{si}]." if si is not None else ""
    pieces = sheet.get("pieces")
    if not isinstance(pieces, list) or not pieces:
        problems.add(f"{where}pieces", "missing or empty", "add at least one piece")
        return None
    if len(pieces) > MAX_PIECES:
        problems.add(f"{where}pieces", f"{len(pieces)} pieces, the limit is {MAX_PIECES}",
                     "split the story into several sheets with \"sheets\": [...]")
    start, local, out = len(problems), set(), []
    for pi, p in enumerate(pieces):
        f = f"{where}pieces[{pi}]"
        if not isinstance(p, dict):
            problems.add(f, "not an object", "write {\"id\", \"shape\", \"label\", \"text\"}")
            continue
        pid = p.get("id")
        if not isinstance(pid, str) or not ID_RE.match(pid):
            problems.add(f"{f}.id", f"\"{pid}\" is not a valid id", "use lowercase letters, digits and dashes")
        elif pid in ids:
            problems.add(f"{f}.id", f"\"{pid}\" is used twice", "give every piece its own id")
        else:
            ids.add(pid)
            local.add(pid)
        if p.get("shape") not in SHAPES:
            problems.add(f"{f}.shape", f"\"{p.get('shape')}\" is not a shape", "use one of: " + ", ".join(SHAPES))
        label = p.get("label")
        if not isinstance(label, str) or not label.strip() or len(label.split()) > MAX_LABEL_WORDS:
            problems.add(f"{f}.label", "missing or longer than three words", "name the piece in one to three words")
        check_text(p.get("text"), f"{f}.text", problems)
        after = p.get("after", [])
        if not isinstance(after, list):
            problems.add(f"{f}.after", "not a list", "write it as [\"id\", ...]")
            after = []
        code = extract(root, p["code"], f"{f}.code", problems) if "code" in p else None
        numbered.append(pid)
        out.append({"id": pid, "shape": p.get("shape"), "label": label, "text": p.get("text"),
                    "after": after, "code": code, "n": len(numbered)})
    for pi, p in enumerate(out):
        for a in p["after"]:
            if a not in local:
                problems.add(f"{where}pieces[{pi}].after", f"\"{a}\" is not a piece on this sheet",
                             "name the id of a piece on the same sheet")
    if len(problems) > start:
        return None
    cycle = find_cycle(out)
    if cycle:
        problems.add(f"{where}pieces[].after", "cycle: " + " > ".join(cycle),
                     "remove one `after` so the story runs one way; a way back is an arrow")
        return None
    rank = ranks(out)
    for p in out:
        p["rank"] = rank[p["id"]]
    arrows = []
    for ai, a in enumerate(sheet.get("arrows", [])):
        f = f"{where}arrows[{ai}]"
        if a.get("from") not in local or a.get("to") not in local:
            problems.add(f, "from/to is not a piece on this sheet", "use two ids from this sheet's pieces")
            continue
        if rank[a["to"]] >= rank[a["from"]]:
            problems.add(f, f"\"{a['to']}\" does not come before \"{a['from']}\"",
                         "an arrow is the error path: it goes back to an earlier piece")
            continue
        check_text(a.get("label"), f"{f}.label", problems)
        arrows.append({"from": a["from"], "to": a["to"], "label": a.get("label")})
    unsure = []
    for ui_, u in enumerate(sheet.get("unsure", [])):
        f = f"{where}unsure[{ui_}]"
        if u.get("after") not in local:
            problems.add(f"{f}.after", f"\"{u.get('after')}\" is not a piece on this sheet",
                         "name the piece the gap comes after")
            continue
        if check_text(u.get("text"), f"{f}.text", problems):
            unsure.append({"after": u["after"], "text": u["text"], "rank": rank[u["after"]] + 1})
    for p in out:
        del p["after"]
    cols = 1 + max([p["rank"] for p in out] + [u["rank"] for u in unsure])
    return {"name": sheet.get("name", ""), "pieces": out, "arrows": arrows,
            "unsure": unsure, "cols": cols}
```

**Step 4: Run test to verify it passes**
Run: `python3 -m unittest discover -s tests -p test_render.py -v`
Expected: PASS, 22 tests OK

**Step 5: Commit**
`git add -A && git commit -m "feat(engine): validate a sheet: shapes, one sentence, 20 pieces, cycles, error arrows"`


### Task 5: render.py: whole document (mode, title, language, sheets, screenshots)

**Lane:** engine

**Files:**
- Modify: `skills/explain/engine/render.py` (append)
- Modify: `tests/test_render.py`

**Step 1: Write the failing test**

Insert above the final `if __name__ == "__main__":` block of `tests/test_render.py`:

```python
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
```

**Step 2: Run test to verify it fails**
Run: `python3 -m unittest discover -s tests -p test_render.py -v`
Expected: FAIL: 12 errors, `AttributeError: module 'render' has no attribute 'build'`

**Step 3: Write minimal implementation**

Append to the end of `skills/explain/engine/render.py`:

```python
def build(doc, root, shots_dir=None):
    """Validate doc, read its code (under root) and screenshots (under shots_dir, default root).
    Returns (data, problems); data is None when there are problems."""
    problems = Problems()
    root = Path(root).resolve()
    shots_dir = Path(shots_dir).resolve() if shots_dir else root
    if not isinstance(doc, dict):
        problems.add("(top)", "not a JSON object", "start from an example in examples/")
        return None, problems
    if doc.get("mode") not in ("walk", "sheet"):
        problems.add("mode", f"\"{doc.get('mode')}\" is not a mode", "use \"walk\" or \"sheet\"")
    title = doc.get("title")
    if not isinstance(title, str) or not title.strip() or len(title.split()) > MAX_TITLE_WORDS:
        problems.add("title", "missing or longer than nine words", "use the user's question in at most nine words")
    lang = doc.get("lang", "")
    if not isinstance(lang, str) or not LANG_RE.match(lang):
        problems.add("lang", f"\"{lang}\" is not a language tag", "use the asker's language, like \"en\" or \"it\"")
        lang = "en"
    custom = doc.get("ui", {})
    unknown = [k for k in custom if k not in UI_KEYS]
    if unknown:
        problems.add("ui", "unknown keys: " + ", ".join(unknown), "use only: " + ", ".join(UI_KEYS))
    base = UI.get(lang.split("-")[0])
    missing = [k for k in UI_KEYS if k not in custom] if base is None else []
    if missing:
        problems.add("ui", f"no built-in words for \"{lang}\"; missing: " + ", ".join(missing),
                     "add \"ui\" with each key translated into the asker's language")
    if "sheets" in doc and "pieces" in doc:
        problems.add("sheets", "both \"sheets\" and top-level \"pieces\"", "use one: \"pieces\" for one sheet, \"sheets\" for several")
        return None, problems
    multi = "sheets" in doc
    sheets_in = doc["sheets"] if multi else [doc]
    if multi and (not isinstance(sheets_in, list) or not sheets_in):
        problems.add("sheets", "missing or empty", "add at least one sheet")
        return None, problems
    ids, numbered, sheets = set(), [], []
    for si, s in enumerate(sheets_in):
        if multi and len(sheets_in) > 1 and not (isinstance(s.get("name"), str) and s["name"].strip()):
            problems.add(f"sheets[{si}].name", "missing", "name each sheet in one to three words")
        sheets.append(check_sheet(s, si if multi else None, ids, root, problems, numbered))
    shots = []
    for i, shot in enumerate(doc.get("shots", [])):
        f = f"shots[{i}]"
        path = inside(shots_dir, str(shot.get("file", "")))
        kind = SHOT_TYPES.get(Path(str(shot.get("file", ""))).suffix.lower())
        if path is None or not path.is_file() or kind is None:
            problems.add(f"{f}.file", f"image {shot.get('file')} not found under {shots_dir}",
                         "use a .png, .jpg, .webp, .gif or .svg path relative to the JSON file")
            continue
        if shot.get("piece") not in ids:
            problems.add(f"{f}.piece", f"\"{shot.get('piece')}\" is not a piece", "name the piece this screenshot shows")
            continue
        check_text(shot.get("tag"), f"{f}.tag", problems)
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        shots.append({"src": f"data:{kind};base64,{data}", "piece": shot["piece"], "tag": shot.get("tag")})
    if problems:
        return None, problems
    ui = dict(base or {})
    ui.update(custom)
    return {"mode": doc["mode"], "title": title_lines(title), "lang": lang, "ui": ui,
            "sheets": sheets, "shots": shots}, problems
```

**Step 4: Run test to verify it passes**
Run: `python3 -m unittest discover -s tests -p test_render.py -v`
Expected: PASS, 34 tests OK

**Step 5: Commit**
`git add -A && git commit -m "feat(engine): validate the document: mode, title, language words, sheets, screenshots"`


### Task 6: render.py CLI and the template shell (Zine styles)

**Lane:** engine

**Files:**
- Modify: `skills/explain/engine/render.py` (append)
- Create: `skills/explain/engine/template.html`
- Modify: `tests/test_render.py`

**Step 1: Write the failing test**

Insert above the final `if __name__ == "__main__":` block of `tests/test_render.py`:

```python
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
```

**Step 2: Run test to verify it fails**
Run: `python3 -m unittest discover -s tests -p test_render.py -v`
Expected: FAIL: 2 errors (`render_html`/`main` missing: the CLI prints nothing and exits 1 with a traceback) and 2 failures on return codes

**Step 3: Write minimal implementation**

Append to the end of `skills/explain/engine/render.py` (`re.sub` substitutes the three placeholders in one pass, so text that contains a placeholder name is never substituted twice):

```python
def render_html(data):
    """Put the data into template.html. '<' is escaped so no text can close the script tag."""
    template = (HERE / "template.html").read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    values = {"LANG": html.escape(data["lang"]), "TITLE": html.escape(" ".join(data["title"])),
              "DATA": payload}
    return re.sub(r"__(LANG|TITLE|DATA)__", lambda m: values[m.group(1)], template)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Render a draw-it-out walk or sheet JSON to one HTML file.")
    ap.add_argument("json", help="walk.json or sheet.json")
    ap.add_argument("--root", default=".", help="project folder that code paths are relative to")
    ap.add_argument("--out", required=True, help="HTML file to write")
    args = ap.parse_args(argv)
    try:
        doc = json.loads(Path(args.json).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        print(f"(file) → cannot read {args.json}: {err} → write valid JSON", file=sys.stderr)
        return 1
    data, problems = build(doc, args.root, Path(args.json).parent)
    if problems:
        print(f"Refused: {len(problems)} problem(s)", file=sys.stderr)
        for line in problems:
            print("- " + line, file=sys.stderr)
        return 1
    Path(args.out).write_text(render_html(data), encoding="utf-8")
    print(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Create `skills/explain/engine/template.html`: the Zine tokens, all styles and the page shell. Its renderer script is a placeholder until Task 8.

```html
<!doctype html>
<html lang="__LANG__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=Inter:wght@400;600&family=Space+Mono:wght@400;700&display=swap">
<style>
:root {
  --ink: #070707; --coal: #111111; --paper: #f3e6c8; --paper-85: #f3e6c8d9; --paper-60: #f3e6c899;
  --pink: #ef4f7a; --pink-deep: #9e2448; --teal: #26b7aa; --mustard: #f6bd33; --mustard-deep: #9c6f06;
  --on-accent: #070707; --focus: #f6bd33;
  --font-display: "Archivo Black", Impact, sans-serif;
  --font-mono: "Space Mono", ui-monospace, monospace;
  --font-sans: Inter, system-ui, sans-serif;
  --tilt-a: -1.2deg; --tilt-b: 0.8deg; --tilt-tag: -12deg;
}
* { box-sizing: border-box; }
html, body { margin: 0; background: var(--ink); color: var(--paper); font-family: var(--font-sans); }
body::after { content: ''; position: fixed; inset: 0; pointer-events: none; opacity: 0.09; z-index: 9;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 240 240' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E"); }
main { max-width: 1280px; margin: 0 auto; padding: 32px 16px 64px; }
button:focus-visible { outline: 2px dashed var(--focus); outline-offset: 4px; }
/* Title: the user's question, one accent per line */
.dio-head { position: relative; display: flex; flex-wrap: wrap; gap: 16px; align-items: flex-start; margin-bottom: 32px; }
.dio-title { font-family: var(--font-display); text-transform: uppercase; letter-spacing: -0.035em; line-height: 0.92;
  font-size: clamp(36px, 9vw, 88px); font-weight: 400; margin: 0; max-width: 100%; overflow-wrap: anywhere; }
.dio-title span { display: block; }
.dio-title span:nth-child(3n+1) { color: var(--paper); } .dio-title span:nth-child(3n+2) { color: var(--teal); } .dio-title span:nth-child(3n) { color: var(--pink); }
.dio-doodles { display: flex; gap: 18px; align-items: center; }
.dio-doodles svg { width: 34px; height: 34px; }
.dio-doodles svg:nth-child(2) { transform: rotate(18deg); } .dio-doodles svg:nth-child(3) { transform: rotate(-24deg); width: 26px; }
/* Controls */
.dio-controls { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 24px; }
.dio-btn { font-family: var(--font-mono); font-size: 14px; letter-spacing: 0.12em; text-transform: uppercase; cursor: pointer;
  background: transparent; color: var(--paper); border: 2px solid var(--paper-85); border-radius: 6px; padding: 8px 16px; }
.dio-btn--play { background: var(--pink); color: var(--on-accent); border-color: var(--pink); box-shadow: 4px 5px 0 0 var(--pink-deep); transform: rotate(-1.5deg); }
/* Screenshots: what you see */
.dio-shots { display: flex; flex-wrap: wrap; gap: 24px; margin: 0 0 24px; }
.dio-shots h2 { flex-basis: 100%; margin: 0; font-family: var(--font-mono); font-size: 12px; letter-spacing: 0.22em; text-transform: uppercase; color: var(--paper-60); font-weight: 400; }
.dio-shot { position: relative; margin: 0; max-width: min(100%, 420px); }
.dio-shot img { display: block; max-width: 100%; height: auto; border: 3px solid var(--paper); border-radius: 4px; }
.dio-tag { position: absolute; left: 8px; top: -12px; background: var(--mustard); color: var(--on-accent); padding: 4px 10px; border-radius: 2px;
  font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.16em; text-transform: uppercase; box-shadow: 3px 3px 0 0 var(--ink); transform: rotate(var(--tilt-tag)); max-width: 90%; }
/* Sheet */
.dio-sheet { position: relative; background: var(--ink); border: 2px solid #f3e6c840; border-radius: 6px; padding: 88px 16px 24px; margin-bottom: 40px; }
.dio-label { position: absolute; right: 16px; top: 16px; display: inline-flex; flex-direction: column; gap: 2px; background: var(--coal);
  border: 2px solid var(--mustard); border-radius: 4px; padding: 8px 14px; transform: rotate(1.5deg); max-width: calc(100% - 32px); }
.dio-label__fig { font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.22em; text-transform: uppercase; color: var(--paper-60); }
.dio-label__title { font-family: var(--font-display); font-size: 16px; line-height: 1.05; text-transform: uppercase; color: var(--mustard); }
.dio-cols { display: flex; flex-wrap: wrap; align-items: flex-start; gap: 32px 12px; }
.dio-col { display: flex; flex-direction: column; gap: 20px; flex: 0 0 200px; min-width: 0; }
.dio-join { flex: none; align-self: center; }
.dio-arrow { position: relative; display: block; width: 36px; height: 3px; background: var(--paper); }
.dio-arrow::after { content: ''; position: absolute; right: -2px; top: -5px; border-left: 9px solid var(--paper); border-top: 6.5px solid transparent; border-bottom: 6.5px solid transparent; }
/* Pieces: one shape, one meaning */
.dio-piece { display: flex; flex-direction: column; gap: 8px; align-items: flex-start; }
.dio-piece:nth-child(odd) { transform: rotate(var(--tilt-a)); } .dio-piece:nth-child(even) { transform: rotate(var(--tilt-b)); }
.dio-shape { position: relative; display: inline-flex; align-items: center; gap: 8px; min-height: 44px; padding: 8px 16px; max-width: 100%;
  font-family: var(--font-display); font-size: 14px; text-transform: uppercase; text-align: left; border: 3px solid var(--ink); border-radius: 6px;
  color: var(--on-accent); overflow-wrap: break-word; }
button.dio-shape { cursor: pointer; }
.dio-n { flex: none; white-space: nowrap; font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.1em; opacity: 0.75; }
.dio-shape--you { background: var(--mustard); border-radius: 9999px; box-shadow: 4px 5px 0 0 var(--mustard-deep); }
.dio-shape--ai { background: var(--pink); box-shadow: 4px 5px 0 0 var(--pink-deep); }
.dio-shape--ai svg { width: 20px; height: 20px; flex: none; }
.dio-shape--check { background: transparent; border-color: transparent; color: var(--teal); padding-left: 4px; }
.dio-shape--check::before { content: ''; flex: none; width: 26px; height: 26px; margin: 4px; background: var(--teal); border: 3px solid var(--ink); outline: 2px solid var(--teal); transform: rotate(45deg); }
.dio-shape--thing { background: var(--paper); border-radius: 4px; font-family: var(--font-mono); letter-spacing: 0.12em; }
.dio-shape--tested { background: var(--paper); margin-top: 12px; box-shadow: 6px 7px 0 0 var(--mustard-deep); }
.dio-studs { position: absolute; left: 12px; right: 12px; top: -14px; display: flex; justify-content: space-around; }
.dio-studs i { display: block; width: 22px; height: 11px; background: var(--paper); border: 2px solid var(--ink); border-bottom: 0; border-radius: 3px 3px 0 0; }
.dio-shape--look { background: var(--ink); color: var(--mustard); border-color: var(--mustard); border-radius: 4px; font-family: var(--font-mono); letter-spacing: 0.12em; }
.dio-text { margin: 0; font-size: 14px; line-height: 1.5; color: var(--paper-85); }
.dio-unsure { border: 3px dashed var(--paper); border-radius: 6px; background: var(--coal); padding: 10px 14px; font-family: var(--font-mono); font-size: 13px; line-height: 1.5; color: var(--paper); }
.dio-unsure::before { content: '? '; color: var(--mustard); }
/* Error path: dashed pink, back one step, below the row */
.dio-backs { display: flex; flex-direction: column; gap: 12px; margin-top: 28px; }
.dio-back { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; }
.dio-back__line { display: block; width: 120px; height: 3px; position: relative; background: repeating-linear-gradient(90deg, var(--pink) 0 9px, transparent 9px 15px); }
.dio-back__line::before { content: ''; position: absolute; left: -2px; top: -5px; border-right: 9px solid var(--pink); border-top: 6.5px solid transparent; border-bottom: 6.5px solid transparent; }
.dio-back__text { font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.16em; text-transform: uppercase; color: var(--paper-60); }
/* Code panel */
.dio-code { margin-top: 24px; background: var(--coal); border: 2px solid #f3e6c840; border-radius: 6px; padding: 12px 0; }
.dio-code[hidden] { display: none; }
.dio-code__head { display: flex; justify-content: space-between; gap: 12px; padding: 0 16px 8px; font-family: var(--font-mono); font-size: 12px; color: var(--mustard); overflow-wrap: anywhere; }
.dio-code pre { margin: 0; overflow-x: auto; font-family: var(--font-mono); font-size: 13px; line-height: 1.6; }
.dio-line { display: flex; padding: 0 16px; white-space: pre; }
.dio-line.is-focus { background: #f6bd3326; box-shadow: inset 3px 0 0 var(--mustard); }
.dio-ln { flex: none; width: 4ch; margin-right: 2ch; text-align: right; color: var(--paper-60); user-select: none; }
/* Legend and stage bar */
.dio-legend { display: inline-flex; flex-direction: column; gap: 8px; background: var(--coal); border: 2px solid #f3e6c840; border-radius: 6px; padding: 14px 18px; margin-top: 28px; max-width: 100%; }
.dio-legend__title { margin: 0 0 2px; font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.22em; text-transform: uppercase; color: var(--paper-60); }
.dio-legend__row { display: flex; align-items: center; gap: 12px; font-family: var(--font-mono); font-size: 13px; }
.dio-sym { flex: none; display: block; width: 34px; height: 18px; border: 2px solid var(--ink); }
.dio-sym--you { background: var(--mustard); border-radius: 9px; } .dio-sym--ai { background: var(--pink); border-radius: 3px; }
.dio-sym--check { width: 16px; height: 16px; margin: 0 9px; background: var(--teal); transform: rotate(45deg); }
.dio-sym--thing { background: var(--paper); border-radius: 2px; } .dio-sym--tested { background: var(--paper); border-radius: 3px; border-top: 5px dotted var(--ink); }
.dio-sym--look { background: var(--ink); border-color: var(--mustard); border-radius: 2px; }
.dio-sym--error { height: 3px; border: 0; background: repeating-linear-gradient(90deg, var(--pink) 0 8px, transparent 8px 13px); }
.dio-sym--unsure { background: var(--coal); border: 2px dashed var(--paper); border-radius: 3px; }
.dio-stages { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 28px; }
.dio-stage { flex: 1 1 120px; text-align: center; padding: 4px 8px; border: 2px solid #f3e6c840; border-radius: 4px; font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.16em; text-transform: uppercase; color: var(--paper-60); }
.dio-stage--done { border-color: var(--teal); color: var(--teal); } .dio-stage--now { border-color: var(--mustard); background: var(--mustard); color: var(--on-accent); }
/* Build-in: stop-motion pop, story order */
.dio-step { opacity: 0; visibility: hidden; }
.dio-step.is-on { opacity: 1; visibility: visible; animation: dio-pop 0.36s steps(3) both; }
@keyframes dio-pop { 0% { opacity: 0; translate: 0 8px; scale: 0.7; } 66% { opacity: 1; scale: 1.06; } 100% { opacity: 1; translate: none; scale: none; } }
@media (max-width: 699px) {
  .dio-cols { flex-direction: column; align-items: stretch; }
  .dio-col { flex-basis: auto; }
  .dio-join { align-self: flex-start; margin: 6px 0 6px 24px; transform: rotate(90deg); }
}
@media (min-width: 700px) { main { padding: 48px; } .dio-sheet { padding: 96px 32px 32px; } .dio-doodles { margin-left: auto; } }
@media (prefers-reduced-motion: reduce) { .dio-step.is-on { animation: none; } }
</style>
</head>
<body>
<main id="dio"></main>
<script id="dio-data" type="application/json">__DATA__</script>
<script>
/* renderer: Task 8 */
</script>
</body>
</html>
```

**Step 4: Run test to verify it passes**
Run: `python3 -m unittest discover -s tests -p test_render.py -v`
Expected: PASS, 39 tests OK

**Step 5: Commit**
`git add -A && git commit -m "feat(engine): render.py CLI and the Zine template shell"`


### Task 7: The two examples (a walk through a tiny shop, an Italian two-sheet process)

**Lane:** engine

**Files:**
- Create: `tests/test_snapshots.py`
- Create: `skills/explain/examples/shop/app/pay-button.js`
- Create: `skills/explain/examples/shop/api/pay.js`
- Create: `skills/explain/examples/shop/lib/db.js`
- Create: `skills/explain/examples/shop/lib/card.js`
- Create: `skills/explain/examples/shop/tests/db.test.js`
- Create: `skills/explain/examples/shop/shots/checkout.svg`
- Create: `skills/explain/examples/walk.json`
- Create: `skills/explain/examples/sheet.json`

**Step 1: Write the failing test**

`tests/test_snapshots.py` (Task 9 adds the snapshot class):

```python
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
```

**Step 2: Run test to verify it fails**
Run: `python3 -m unittest discover -s tests -p test_snapshots.py -v`
Expected: FAIL: 2 failures, render exits 1 with `(file) → cannot read …/examples/walk.json`

**Step 3: Write minimal implementation**

`skills/explain/examples/shop/app/pay-button.js` (walk.json cites these line numbers: keep every line as written):

```js
// The Pay button on the checkout page.
import { showOrder, showError } from "./screens.js";

export function PayButton({ cart }) {
  async function onClick() {
    const res = await fetch("/api/pay", {
      method: "POST",
      body: JSON.stringify({ cartId: cart.id, card: cart.card }),
    });
    const body = await res.json();
    if (!res.ok) return showError(body.error);
    showOrder(body.order, body.note);
  }
  return `<button onclick="${onClick}">Pay ${cart.total}</button>`;
}
```

`skills/explain/examples/shop/api/pay.js` (walk.json cites these line numbers: keep every line as written):

```js
// POST /api/pay: checks the cart and the card, saves the order, writes a thank-you note.
import { loadCart, saveOrder } from "../lib/db.js";
import { cardLooksValid } from "../lib/card.js";
import { ai } from "../lib/ai.js";

export async function POST(req) {
  const { cartId, card } = await req.json();
  const cart = await loadCart(cartId);
  if (!cart || cart.items.length === 0) {
    return Response.json({ error: "Your cart is empty." }, { status: 400 });
  }
  if (!cardLooksValid(card)) {
    return Response.json({ error: "That card number doesn't look right." }, { status: 402 });
  }
  const order = await saveOrder(cart, card.last4);
  const note = await ai.write(`A two-line thank-you note for an order of ${cart.items.length} items.`);
  return Response.json({ order, note });
}
```

`skills/explain/examples/shop/lib/db.js` (walk.json cites these line numbers: keep every line as written):

```js
// The database: carts in, orders out.
import { sql } from "./sql.js";

export async function loadCart(id) {
  return sql`select * from carts where id = ${id}`.first();
}

export async function saveOrder(cart, last4) {
  const [order] = await sql`
    insert into orders (cart_id, total, card_last4)
    values (${cart.id}, ${cart.total}, ${last4})
    returning id, total`;
  return order;
}
```

`skills/explain/examples/shop/lib/card.js` (walk.json cites these line numbers: keep every line as written):

```js
// A quick check that a card number could be real (the Luhn check). It never charges anything.
export function cardLooksValid(card) {
  const digits = String(card?.number ?? "").replace(/\D/g, "");
  if (digits.length < 12) return false;
  let sum = 0;
  for (let i = 0; i < digits.length; i++) {
    let d = Number(digits[digits.length - 1 - i]);
    if (i % 2 === 1) d = d * 2 > 9 ? d * 2 - 9 : d * 2;
    sum += d;
  }
  return sum % 10 === 0;
}
```

`skills/explain/examples/shop/tests/db.test.js` (walk.json cites these line numbers: keep every line as written):

```js
import { test, expect } from "vitest";
import { saveOrder } from "../lib/db.js";

test("saveOrder stores the total and the last four digits", async () => {
  const order = await saveOrder({ id: 7, total: 42 }, "4242");
  expect(order.total).toBe(42);
});
```

`skills/explain/examples/shop/shots/checkout.svg` (walk.json cites these line numbers: keep every line as written):

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 240" width="400" height="240">
  <rect width="400" height="240" fill="#ffffff"/>
  <text x="24" y="44" font-family="sans-serif" font-size="22" fill="#222222">Checkout</text>
  <text x="24" y="92" font-family="sans-serif" font-size="15" fill="#555555">2 items · 42.00</text>
  <rect x="24" y="150" width="160" height="48" rx="8" fill="#2f6fde"/>
  <text x="70" y="180" font-family="sans-serif" font-size="17" fill="#ffffff">Pay 42.00</text>
</svg>
```

`skills/explain/examples/walk.json` (code paths under `--root examples`, the shot next to the JSON):

```json
{
  "mode": "walk",
  "title": "What happens when I click Pay?",
  "lang": "en",
  "pieces": [
    {"id": "click", "shape": "you", "label": "Click Pay", "text": "You press the Pay button on the checkout page.",
     "code": {"file": "shop/app/pay-button.js", "lines": "4-15", "focus": "5"}},
    {"id": "request", "shape": "thing", "label": "Pay request", "text": "The page sends your cart and card to the server.",
     "code": {"file": "shop/app/pay-button.js", "lines": "6-9"}, "after": ["click"]},
    {"id": "cart", "shape": "check", "label": "Cart not empty", "text": "The server stops here if your cart has nothing in it.",
     "code": {"file": "shop/api/pay.js", "lines": "8-11", "focus": "9"}, "after": ["request"]},
    {"id": "card", "shape": "check", "label": "Card looks real", "text": "A quick math check on the card number, which charges nothing.",
     "code": {"file": "shop/lib/card.js", "lines": "2-12"}, "after": ["cart"]},
    {"id": "save", "shape": "tested", "label": "Save order", "text": "The order is written to the database, and a test checks this part.",
     "code": {"file": "shop/lib/db.js", "lines": "8-14", "focus": "9-12"}, "after": ["card"]},
    {"id": "note", "shape": "ai", "label": "Thank-you note", "text": "An AI writes a short thank-you note, a little different every time.",
     "code": {"file": "shop/api/pay.js", "lines": "16"}, "after": ["save"]},
    {"id": "done", "shape": "look", "label": "Order page", "text": "You see your order number and the note.",
     "code": {"file": "shop/app/pay-button.js", "lines": "10-12", "focus": "12"}, "after": ["note"]}
  ],
  "arrows": [
    {"from": "card", "to": "click", "label": "Card refused, you try again"}
  ],
  "unsure": [
    {"after": "note", "text": "I didn't see whether the note is also sent by email."}
  ],
  "shots": [
    {"file": "shop/shots/checkout.svg", "piece": "click", "tag": "The Pay button"}
  ]
}
```

`skills/explain/examples/sheet.json`:

```json
{
  "mode": "sheet",
  "title": "Come arriva online una modifica?",
  "lang": "it",
  "sheets": [
    {
      "name": "La proposta",
      "pieces": [
        {"id": "ask", "shape": "you", "label": "Chiedi", "text": "Chiedi all'AI di cambiare il colore del bottone."},
        {"id": "change", "shape": "ai", "label": "Modifica", "text": "L'AI scrive la modifica, e due volte non la scrive mai uguale.", "after": ["ask"]},
        {"id": "pr", "shape": "thing", "label": "Pull request", "text": "La modifica diventa una richiesta da approvare.", "after": ["change"]},
        {"id": "tests", "shape": "check", "label": "Test automatici", "text": "I test girano da soli e dicono sì o no.", "after": ["pr"]}
      ],
      "arrows": [
        {"from": "tests", "to": "change", "label": "Test rossi"}
      ]
    },
    {
      "name": "Online",
      "pieces": [
        {"id": "review", "shape": "you", "label": "Approvi", "text": "Guardi la modifica e la approvi."},
        {"id": "merge", "shape": "tested", "label": "Unione", "text": "La modifica entra nel codice principale, coperta dai test.", "after": ["review"]},
        {"id": "live", "shape": "look", "label": "Online", "text": "Il bottone nuovo è online per tutti.", "after": ["merge"]}
      ],
      "unsure": [
        {"after": "live", "text": "Non ho visto quanto tempo passa prima che sia online."}
      ]
    }
  ]
}
```

**Step 4: Run test to verify it passes**
Run: `python3 -m unittest discover -s tests -p test_snapshots.py -v`
Expected: PASS, 2 tests OK

**Step 5: Commit**
`git add -A && git commit -m "feat(engine): walk and sheet examples"`


### Task 8: The renderer: columns, build-in, code panel, shots, legend, StageBar

**Lane:** engine

**Files:**
- Modify: `skills/explain/engine/template.html` (the `/* renderer: Task 8 */` line)
- Create: `tests/test_browser.py`

**Step 1: Write the failing test**

Needs Playwright for Python and a browser: `pip install playwright && python3 -m playwright install chromium` (a system Chrome also works: the test falls back to `channel="chrome"`). Without them these tests skip, so Step 2 cannot show a failure: install first.

`tests/test_browser.py`:

```python
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


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**
Run: `python3 -m unittest discover -s tests -p test_browser.py -v`
Expected: FAIL: 2 failures and 1 error (no `.dio-piece` or `.dio-step` exists, `wait_for_function` times out, no code panel)

**Step 3: Write minimal implementation**

In `skills/explain/engine/template.html`, replace the line `/* renderer: Task 8 */` with this (all data reaches the page through `textContent`, never `innerHTML`; only the fixed die, studs and doodle SVGs use markup):

```js
(function () {
  var D = JSON.parse(document.getElementById('dio-data').textContent);
  var root = document.getElementById('dio');
  var DIE = '<svg viewBox="0 0 100 100" aria-hidden="true"><rect x="8" y="8" width="84" height="84" rx="18" fill="none" stroke="currentColor" stroke-width="9"/><circle cx="30" cy="30" r="9" fill="currentColor"/><circle cx="70" cy="30" r="9" fill="currentColor"/><circle cx="50" cy="50" r="9" fill="currentColor"/><circle cx="30" cy="70" r="9" fill="currentColor"/><circle cx="70" cy="70" r="9" fill="currentColor"/></svg>';
  var DOODLES = '<svg viewBox="0 0 40 40" aria-hidden="true"><path d="M20 3v34M5 11l30 18M5 29l30-18" stroke="#ef4f7a" stroke-width="4" stroke-linecap="round" fill="none"/></svg>' +
    '<svg viewBox="0 0 40 40" aria-hidden="true"><path d="M20 2c1.5 10 4 14.5 18 18-14 3.5-16.5 8-18 18-1.5-10-4-14.5-18-18 14-3.5 16.5-8 18-18z" fill="#f3e6c8"/></svg>' +
    '<svg viewBox="0 0 40 40" aria-hidden="true"><path d="M6 9l29 22M33 6L9 35" stroke="#f3e6c8" stroke-width="4.5" stroke-linecap="round" fill="none"/></svg>';
  var step = 0;
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function stepped(e) { e.classList.add('dio-step'); e.dataset.step = step++; return e; }
  var byId = {};
  D.sheets.forEach(function (s) { s.pieces.forEach(function (p) { byId[p.id] = p; }); });

  var head = el('header', 'dio-head');
  var h1 = el('h1', 'dio-title');
  D.title.forEach(function (line) { h1.appendChild(el('span', null, line)); });
  head.appendChild(h1);
  var dd = el('div', 'dio-doodles'); dd.innerHTML = DOODLES; dd.setAttribute('aria-hidden', 'true');
  head.appendChild(dd);
  root.appendChild(head);

  var controls = el('div', 'dio-controls');
  var play = el('button', 'dio-btn dio-btn--play', '▶ ' + D.ui.replay);
  var prev = el('button', 'dio-btn', '← ' + D.ui.prev);
  var next = el('button', 'dio-btn', D.ui.next + ' →');
  controls.append(play, prev, next);
  root.appendChild(controls);

  function codePanel(sheetEl) {
    var panel = el('section', 'dio-code'); panel.hidden = true;
    var headRow = el('div', 'dio-code__head');
    var where = el('span');
    var close = el('button', 'dio-btn', D.ui.close);
    close.addEventListener('click', function () { panel.hidden = true; });
    headRow.append(where, close);
    var pre = el('pre');
    panel.append(headRow, pre);
    sheetEl.appendChild(panel);
    return function show(code, btn) {
      where.textContent = code.file + ':' + code.start + '-' + code.end;
      pre.textContent = '';
      code.lines.forEach(function (text, i) {
        var n = code.start + i;
        var row = el('div', 'dio-line' + (code.focus.indexOf(n) >= 0 ? ' is-focus' : ''));
        row.append(el('span', 'dio-ln', String(n)), el('span', 'dio-tx', text));
        pre.appendChild(row);
      });
      panel.hidden = false;
      panel.scrollIntoView({ block: 'nearest' });
    };
  }

  function pieceEl(p, showCode) {
    var box = el('div', 'dio-piece');
    box.dataset.id = p.id;
    var shape = el(p.code ? 'button' : 'div', 'dio-shape dio-shape--' + p.shape);
    if (p.shape === 'ai') shape.insertAdjacentHTML('beforeend', DIE);
    if (p.shape === 'tested') shape.insertAdjacentHTML('beforeend', '<span class="dio-studs" aria-hidden="true"><i></i><i></i><i></i></span>');
    shape.append(el('span', 'dio-n', pad(p.n)), el('span', null, p.label));
    if (p.code) shape.addEventListener('click', function () { showCode(p.code, shape); });
    box.append(shape, el('p', 'dio-text', p.text));
    return box;
  }

  D.sheets.forEach(function (s, si) {
    var shots = D.shots.filter(function (sh) { return s.pieces.some(function (p) { return p.id === sh.piece; }); });
    if (shots.length) {
      var strip = el('section', 'dio-shots');
      strip.appendChild(el('h2', null, D.ui.see));
      shots.forEach(function (sh) {
        var fig = el('figure', 'dio-shot');
        var img = el('img'); img.src = sh.src; img.alt = sh.tag;
        fig.append(img, el('figcaption', 'dio-tag', '→ ' + pad(byId[sh.piece].n) + ' · ' + sh.tag));
        strip.appendChild(fig);
      });
      root.appendChild(strip);
    }
    var sheet = el('section', 'dio-sheet');
    var label = el('div', 'dio-label');
    label.appendChild(el('span', 'dio-label__fig', D.ui.sheet + ' ' + pad(si + 1)));
    if (s.name) label.appendChild(el('span', 'dio-label__title', s.name));
    sheet.appendChild(label);
    var cols = el('div', 'dio-cols');
    var colEls = [], joins = [];
    for (var c = 0; c < s.cols; c++) {
      if (c > 0) { var j = el('span', 'dio-join'); j.appendChild(el('span', 'dio-arrow')); cols.appendChild(j); joins[c] = j; }
      colEls[c] = el('div', 'dio-col'); cols.appendChild(colEls[c]);
    }
    sheet.appendChild(cols);
    var backs = el('div', 'dio-backs');
    sheet.appendChild(backs);
    var showCode = codePanel(sheet);
    var entered = {};
    function enter(col) { if (col > 0 && !entered[col]) { entered[col] = true; stepped(joins[col]); } }
    s.pieces.forEach(function (p) {
      enter(p.rank);
      colEls[p.rank].appendChild(stepped(pieceEl(p, showCode)));
      s.unsure.filter(function (u) { return u.after === p.id; }).forEach(function (u) {
        enter(u.rank);
        colEls[u.rank].appendChild(stepped(el('div', 'dio-unsure', u.text)));
      });
      s.arrows.filter(function (a) { return a.from === p.id; }).forEach(function (a) {
        var row = el('div', 'dio-back');
        var to = byId[a.to];
        row.append(el('span', 'dio-back__line'), el('span', 'dio-back__text', a.label + ' · ' + D.ui.back_to + ' ' + pad(to.n) + ' ' + to.label));
        backs.appendChild(stepped(row));
      });
    });
    if (si === 0) {
      var used = [];
      D.sheets.forEach(function (x) {
        x.pieces.forEach(function (p) { if (used.indexOf(p.shape) < 0) used.push(p.shape); });
        if (x.arrows.length && used.indexOf('error') < 0) used.push('error');
        if (x.unsure.length && used.indexOf('unsure') < 0) used.push('unsure');
      });
      var legend = el('div', 'dio-legend');
      legend.appendChild(el('p', 'dio-legend__title', D.ui.legend));
      ['you', 'ai', 'check', 'thing', 'tested', 'look', 'error', 'unsure'].forEach(function (k) {
        if (used.indexOf(k) < 0) return;
        var row = el('div', 'dio-legend__row');
        row.append(el('span', 'dio-sym dio-sym--' + k), el('span', null, D.ui[k]));
        legend.appendChild(row);
      });
      sheet.insertBefore(legend, sheet.querySelector('.dio-code'));
    }
    if (D.sheets.length > 1) {
      var bar = el('div', 'dio-stages');
      D.sheets.forEach(function (x, xi) {
        bar.appendChild(el('span', 'dio-stage' + (xi < si ? ' dio-stage--done' : xi === si ? ' dio-stage--now' : ''), (xi + 1) + ' · ' + x.name));
      });
      sheet.insertBefore(bar, sheet.querySelector('.dio-code'));
    }
    root.appendChild(sheet);
  });

  var items = Array.prototype.slice.call(document.querySelectorAll('.dio-step'));
  var shown = 0, timer = null;
  var still = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  function show(n) {
    shown = Math.max(0, Math.min(n, items.length));
    items.forEach(function (e, i) { e.classList.toggle('is-on', i < shown); });
  }
  function stop() { if (timer) { clearInterval(timer); timer = null; } }
  function run() {
    stop(); show(0);
    timer = setInterval(function () { show(shown + 1); if (shown >= items.length) stop(); }, 500);
  }
  play.addEventListener('click', function () { if (still) show(items.length); else run(); });
  prev.addEventListener('click', function () { stop(); show(shown - 1); });
  next.addEventListener('click', function () { stop(); show(shown + 1); });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowLeft') { stop(); show(shown - 1); }
    if (e.key === 'ArrowRight') { stop(); show(shown + 1); }
  });
  if (still) show(items.length); else run();
})();
```

**Step 4: Run test to verify it passes**
Run: `python3 -m unittest discover -s tests -p test_browser.py -v`
Expected: PASS, 5 tests OK (piece count, reduced motion shows all, build starts empty, no scroll at 390px, code panel shows `shop/api/pay.js:8-11` with 4 lines and 1 focus line)

**Step 5: Commit**
`git add -A && git commit -m "feat(engine): template renderer with build-in, code panel, shots, legend and StageBar"`


### Task 9: HTML snapshots of the examples

**Lane:** engine

**Files:**
- Modify: `tests/test_snapshots.py`
- Create: `tests/snapshots/walk.html`, `tests/snapshots/sheet.html` (written by the test)

**Step 1: Write the failing test**

Insert above the final `if __name__ == "__main__":` block of `tests/test_snapshots.py`:

```python
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
```

**Step 2: Run test to verify it fails**
Run: `python3 -m unittest discover -s tests -p test_snapshots.py -v`
Expected: FAIL: 2 failures, `snapshot written to …/tests/snapshots/walk.html: review it, then rerun without UPDATE_SNAPSHOTS` (and sheet.html)

**Step 3: Write minimal implementation**

No code: Step 2 wrote both snapshots. Review them: each is the full template with one `dio-data` JSON block; it holds no absolute path (the code paths are relative, the shot is a `data:` URI). Open `tests/snapshots/walk.html` in a browser and check the sheet draws.

**Step 4: Run test to verify it passes**
Run: `python3 -m unittest discover -s tests -p test_snapshots.py -v`
Expected: PASS, 4 tests OK

**Step 5: Commit**
`git add -A && git commit -m "test(engine): HTML snapshots of the walk and sheet examples"`


### Task 10: capture.py: read-only localhost screenshots

**Lane:** capture

**Files:**
- Create: `skills/explain/engine/capture.py`
- Create: `tests/test_capture.py`

**Step 1: Write the failing test**

`tests/test_capture.py` (the `CaptureSmoke` class needs Playwright and a browser, as in Task 8, and skips without them):

```python
"""capture.py: the safety rules without a browser, then one real capture when Playwright is there."""
import http.server
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from helpers import ENGINE
import capture as C

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


class Safety(unittest.TestCase):
    def test_only_localhost_pages(self):
        self.assertTrue(C.is_local("http://localhost:3000/checkout"))
        self.assertTrue(C.is_local("http://127.0.0.1:8000"))
        self.assertTrue(C.is_local("http://[::1]:5173/"))
        self.assertFalse(C.is_local("https://example.com"))
        self.assertFalse(C.is_local("http://localhost.evil.com"))
        self.assertFalse(C.is_local("file:///etc/passwd"))

    def test_only_read_requests_to_localhost(self):
        self.assertTrue(C.allow_request("GET", "http://localhost:3000/app.js"))
        self.assertFalse(C.allow_request("POST", "http://localhost:3000/api/pay"))
        self.assertFalse(C.allow_request("PUT", "http://localhost:3000/api/cart"))
        self.assertFalse(C.allow_request("GET", "https://fonts.example.com/a.woff2"))

    def test_steps_keep_their_order(self):
        args = C.parse(["http://localhost:3000", "--out", "a.png", "--click", "text=Pay", "--wait", "500", "--click", "#ok"])
        self.assertEqual(args.steps, [("click", "text=Pay"), ("wait", "500"), ("click", "#ok")])

    def test_remote_url_refused_before_any_browser(self):
        res = subprocess.run([sys.executable, str(ENGINE / "capture.py"), "https://example.com", "--out", "x.png"],
                             capture_output=True, text=True)
        self.assertEqual(res.returncode, 2)
        self.assertIn("only http(s)://localhost", res.stderr)

    def test_wait_capped(self):
        with self.assertRaises(SystemExit):
            C.parse(["http://localhost:3000", "--out", "a.png", "--wait", "60000"])


class Recorder(http.server.BaseHTTPRequestHandler):
    seen = []
    PAGE = (b'<form method="post" action="/pay"><button id="pay">Pay</button></form>'
            b'<script>fetch("/api/pay", {method: "POST"})</script>')

    def do_GET(self):
        Recorder.seen.append(("GET", self.path))
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(self.PAGE)

    def do_POST(self):
        Recorder.seen.append(("POST", self.path))
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):
        pass


@unittest.skipIf(sync_playwright is None, "playwright not installed")
class CaptureSmoke(unittest.TestCase):
    def test_click_on_submit_never_reaches_the_server(self):
        server = http.server.HTTPServer(("127.0.0.1", 0), Recorder)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "shot.png"
            res = subprocess.run([sys.executable, str(ENGINE / "capture.py"),
                                  f"http://127.0.0.1:{server.server_port}/", "--out", str(out),
                                  "--click", "#pay", "--wait", "300"], capture_output=True, text=True)
            server.shutdown()
            if res.returncode == 3 or "Executable doesn't exist" in res.stderr:
                self.skipTest("no browser")
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertTrue(out.exists())
        self.assertIn(("GET", "/"), Recorder.seen)
        self.assertFalse([s for s in Recorder.seen if s[0] == "POST"])


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**
Run: `python3 -m unittest discover -s tests -p test_capture.py -v`
Expected: FAIL: `ModuleNotFoundError: No module named 'capture'`

**Step 3: Write minimal implementation**

`skills/explain/engine/capture.py` (Playwright is imported only inside `main`, so the safety checks run without it; exit 2 for a bad URL comes from argparse before any browser starts):

```python
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
```

**Step 4: Run test to verify it passes**
Run: `python3 -m unittest discover -s tests -p test_capture.py -v`
Expected: PASS, 6 tests OK (5 without Playwright, 1 skipped)

**Step 5: Commit**
`git add -A && git commit -m "feat(capture): read-only localhost screenshots with declared clicks and waits"`


### Task 11: SKILL.md: trigger and routing

**Lane:** skill

**Files:**
- Create: `skills/explain/SKILL.md`
- Create: `tests/test_skill_docs.py`

**Step 1: Write the failing test**

`tests/test_skill_docs.py` (Tasks 12 and 13 add classes above the `__main__` block):

```python
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
```

**Step 2: Run test to verify it fails**
Run: `python3 -m unittest discover -s tests -p test_skill_docs.py -v`
Expected: FAIL: 2 errors, `FileNotFoundError: …/skills/explain/SKILL.md`

**Step 3: Write minimal implementation**

`skills/explain/SKILL.md`:

````markdown
---
name: explain
description: Explains code or a process as a drawing that builds itself, in plain words for people who don't read code. Use when someone asks "what happens when I click X", "how does this part of my app work", "walk me through this flow", or asks to explain, draw or visualise a process, pipeline, agent loop or business flow.
---

# Draw it out

You explain one thing as a **sheet**: a drawing that builds itself piece by piece. The reader
built software with AI and can't read the code, so every word on the sheet is plain.

## Pick the mode

- **walk**: the question is what *their own code* does when they do something ("what happens
  when I click Pay?", "where does my signup form go?"). Read [walk.md](walk.md).
- **sheet**: the question is how a process works (a pipeline, an agent loop, a business flow,
  a document they shared). Code is optional. Read [sheet.md](sheet.md).

Not sure which? Ask one question: "Should I follow it through your code, or draw the process?"
Read only the mode's file, then [schema.md](schema.md) for the JSON you write.

## Rules for every sheet

- Write in the asker's language, whatever it is: `text`, `label`, `title` and `lang`. For a
  language other than English or Italian, also fill `ui` (schema.md).
- Plain words, short sentences. Explain each technical term the first time it appears
  ("the server: the computer that runs your app's code").
- Never describe what you didn't see. A gap goes in `unsure`, said plainly.
- Code reaches the sheet only through `render.py`: you write `{"file", "lines"}`, never the code.
- Read-only: never edit the project, submit a form, sign in or pay.

## Render

Write the JSON (and any screenshots) to a folder outside the project, such as your scratchpad
or a temp folder, then run:

```
python3 <this skill's folder>/engine/render.py <folder>/walk.json --root <project folder> --out <folder>/walk.html
```

`--root` is the folder that code paths start from; screenshot paths start from the JSON's folder.
Exit 1 prints one line per problem: `field → problem → how to fix`. Fix the JSON and rerun,
at most three times. Still refused: stop and tell the user, in plain words, what is missing.

## Show it

- An Artifact tool is available: publish the HTML file as an artifact.
- Claude Code without one: give the path and open it (`open` on macOS, `xdg-open` on Linux,
  `start` on Windows).
- claude.ai without one: share the HTML file.

Then two or three lines: what the sheet shows, the one piece to look at, and any gap from `unsure`.
````

**Step 4: Run test to verify it passes**
Run: `python3 -m unittest discover -s tests -p test_skill_docs.py -v`
Expected: PASS, 2 tests OK

**Step 5: Commit**
`git add -A && git commit -m "feat(skill): explain skill entry, routing to walk or sheet"`


### Task 12: walk.md and sheet.md: the two procedures

**Lane:** skill

**Files:**
- Create: `skills/explain/walk.md`
- Create: `skills/explain/sheet.md`
- Modify: `tests/test_skill_docs.py`

**Step 1: Write the failing test**

Insert above the final `if __name__ == "__main__":` block of `tests/test_skill_docs.py`:

```python
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
```

**Step 2: Run test to verify it fails**
Run: `python3 -m unittest discover -s tests -p test_skill_docs.py -v`
Expected: FAIL: 2 errors, `FileNotFoundError: …/skills/explain/walk.md`

**Step 3: Write minimal implementation**

`skills/explain/walk.md`:

````markdown
# walk: follow a real path through the code

## 1. Ask, at most three questions

One at a time, and skip any the request already answers:

1. What do you do? (the click, the command, the form)
2. Where does it start? (the page, the screen, the command line)
3. What do you expect to see at the end?

## 2. Read the real path

Follow it in order: where it starts (button, command) → the code that handles it → the checks
→ what gets stored → what comes back. Open every file you use; Grep for names to find the next
one. Note the line numbers as you read. Only files you opened go into the JSON.

## 3. One piece per step

| What you found | Shape |
|---|---|
| the click, the command, a wait | `you` |
| a call to an AI model in their code | `ai` |
| an `if`, a validation, a permission check | `check` |
| a request, a file, a database row | `thing` |
| code that a test you opened calls | `tested` |
| the one result that matters, usually last | `look` |

- Each piece: a 1–3 word `label`, one plain sentence of `text`, and `code` with the exact lines.
- `after` holds the piece (or pieces) that come right before it.
- Where a check fails, add an `arrows` entry back to the piece the user returns to; its `label`
  says why, in their words ("Card refused, you try again").
- Anything you couldn't follow (a background job, an email provider, a file you couldn't find)
  goes in `unsure`, after the last piece you did see.
- More than 20 pieces: split into several sheets (schema.md).

## 4. Screenshots, optional

- **Claude Code, app running locally**: one PNG per screen worth showing, into the JSON's folder:

  ```
  python3 <this skill's folder>/engine/capture.py http://localhost:3000/checkout --out <folder>/checkout.png --click "text=Pay" --wait 1000
  ```

  Only `--click` and `--wait` (milliseconds or a selector). It opens only localhost and blocks
  every request that is not a read, so a click on Pay shows the page but sends nothing.
  Never ask the user to sign in for a screenshot. Exit 3 means Playwright is missing: go on
  without screenshots.
- **claude.ai**: the screenshots the user uploaded, if any.
- Otherwise none: the sheet is code only.

Each shot names the piece it shows (`piece`) and a short `tag`.

## 5. Render and show

`"mode": "walk"`, the user's question as `title`. Render and show as SKILL.md says.
````

`skills/explain/sheet.md`:

```markdown
# sheet: draw a process

## 1. Ask, at most three questions

One at a time, and skip any the request already answers:

1. What process? (name it, or share the document that describes it)
2. Where does it start, and where does it end?
3. Who or what takes part? (people, AI, code, other services)

## 2. Read the source

The user's description, a document they shared, or code if they point you at some. Only
claims the source supports go on the sheet; anything it leaves open goes in `unsure`.

## 3. One piece per step

| What the step is | Shape |
|---|---|
| a person acts or waits | `you` |
| an AI model decides or writes (different answer each time) | `ai` |
| a rule or code check (same answer every time) | `check` |
| a thing that moves: a file, a request, a message, a record | `thing` |
| a step that is verified and reused | `tested` |
| the one result that matters | `look` |

- Each piece: a 1–3 word `label` and one plain sentence of `text`.
- `code` only when you read the code behind a step.
- `after` holds the step (or steps) that come right before it; a way back is an `arrows` entry.
- About 20 pieces is the most for one sheet. A longer process becomes several sheets, each
  named in 1–3 words, in the order the process runs (schema.md).

## 4. Render and show

`"mode": "sheet"`, the user's question as `title`. Render and show as SKILL.md says.
```

**Step 4: Run test to verify it passes**
Run: `python3 -m unittest discover -s tests -p test_skill_docs.py -v`
Expected: PASS, 4 tests OK

**Step 5: Commit**
`git add -A && git commit -m "feat(skill): walk and sheet procedures"`


### Task 13: schema.md: the JSON vocabulary

**Lane:** skill

**Files:**
- Create: `skills/explain/schema.md`
- Modify: `tests/test_skill_docs.py`

**Step 1: Write the failing test**

Insert above the final `if __name__ == "__main__":` block of `tests/test_skill_docs.py`:

```python
class Schema(unittest.TestCase):
    def test_schema_names_every_shape_and_ui_key(self):
        text = (SKILL / "schema.md").read_text(encoding="utf-8")
        for shape in R.SHAPES:
            self.assertIn(f"`{shape}`", text)
        for key in R.UI_KEYS:
            self.assertIn(f"`{key}`", text)
        self.assertIn(f"at most {R.MAX_PIECES}", text)
        self.assertIn("at most nine words", text)
```

**Step 2: Run test to verify it fails**
Run: `python3 -m unittest discover -s tests -p test_skill_docs.py -v`
Expected: FAIL: 1 error, `FileNotFoundError: …/skills/explain/schema.md`

**Step 3: Write minimal implementation**

`skills/explain/schema.md`:

````markdown
# The JSON you write

One object. `render.py` checks it and refuses anything outside these rules.

```json
{
  "mode": "walk",
  "title": "What happens when I click Pay?",
  "lang": "en",
  "pieces": [
    {"id": "click", "shape": "you", "label": "Click Pay", "text": "You press the Pay button.",
     "code": {"file": "app/pay-button.js", "lines": "4-15", "focus": "5"}},
    {"id": "card", "shape": "check", "label": "Card looks real", "text": "A math check on the card number.",
     "code": {"file": "lib/card.js", "lines": "2-12"}, "after": ["click"]}
  ],
  "arrows": [{"from": "card", "to": "click", "label": "Card refused, you try again"}],
  "unsure": [{"after": "card", "text": "I didn't see where the receipt email leaves."}],
  "shots": [{"file": "checkout.png", "piece": "click", "tag": "The Pay button"}]
}
```

Full examples: `examples/walk.json` (code, a screenshot, a gap) and `examples/sheet.json`
(Italian, two sheets).

## Fields

| Field | Rule |
|---|---|
| `mode` | `"walk"` or `"sheet"` |
| `title` | the user's question, at most nine words; drawn uppercase in 2–3 lines |
| `lang` | the asker's language tag: `"en"`, `"it"`, `"de"`, `"pt-BR"` … |
| `ui` | needed when `lang` is not `en` or `it`: every key below, translated |
| `pieces[]` | at most 20 per sheet |
| `pieces[].id` | lowercase letters, digits, dashes; unique across the document |
| `pieces[].shape` | one of `you`, `ai`, `check`, `thing`, `tested`, `look` |
| `pieces[].label` | one to three words, shown on the shape |
| `pieces[].text` | exactly one sentence, shown under the shape |
| `pieces[].code` | optional: `file` relative to `--root`, `lines` `"12-30"` or `"12"`, optional `focus` `"14,20-22"` inside `lines` |
| `pieces[].after` | optional list of ids on the same sheet that come right before; no loops |
| `arrows[]` | the error path only: `from` a piece back `to` an earlier one, `label` one sentence |
| `unsure[]` | `after` a piece id, `text` one sentence: a gap you didn't see |
| `shots[]` | `file` (.png .jpg .webp .gif .svg) relative to the JSON's folder, `piece` id, `tag` short |
| `sheets[]` | instead of top-level `pieces`/`arrows`/`unsure`, for more than 20 pieces: each `{"name", "pieces", "arrows", "unsure"}`, `name` one to three words |

## Shapes

| Shape | Drawn as | Means |
|---|---|---|
| `you` | mustard pill | the person: a click, a command, a wait |
| `ai` | pink box with a die | an AI call: a different answer each time |
| `check` | teal diamond | a check: the same answer every time |
| `thing` | paper box | a file, a request, a saved row |
| `tested` | paper block with studs | a piece covered by tests |
| `look` | mustard outline | look here: the result that matters |
| arrow | dashed pink, back | the error path |
| unsure | dashed box | a gap you declared |

## `ui` keys

`sheet`, `legend`, `replay`, `prev`, `next`, `see`, `close`, `back_to`, `you`, `ai`, `check`,
`thing`, `tested`, `error`, `look`, `unsure`. The last eight are the legend rows; see the English
values in `engine/render.py` (`UI["en"]`).
````

**Step 4: Run test to verify it passes**
Run: `python3 -m unittest discover -s tests -p test_skill_docs.py -v`
Expected: PASS, 5 tests OK

**Step 5: Commit**
`git add -A && git commit -m "feat(skill): schema of shapes, fields and limits"`


### Task 14: pack.sh: the claude.ai skill zip

**Lane:** pack

**Files:**
- Create: `scripts/pack.sh`
- Create: `tests/test_pack.py`

**Step 1: Write the failing test**

`tests/test_pack.py` (Task 15 adds a class above the `__main__` block):

```python
"""scripts/pack.sh builds the claude.ai zip with explain/ at its root."""
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

from helpers import REPO


class Pack(unittest.TestCase):
    def test_zip_holds_the_skill_and_nothing_else(self):
        (REPO / "skills/explain/engine/__pycache__").mkdir(exist_ok=True)
        (REPO / "skills/explain/engine/__pycache__/x.pyc").write_bytes(b"x")
        with tempfile.TemporaryDirectory() as tmp:
            res = subprocess.run(["bash", str(REPO / "scripts/pack.sh"), tmp], capture_output=True, text=True)
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


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**
Run: `python3 -m unittest discover -s tests -p test_pack.py -v`
Expected: FAIL: 1 failure, return code 127 (`bash: …/scripts/pack.sh: No such file or directory`)

**Step 3: Write minimal implementation**

`scripts/pack.sh`:

```bash
#!/usr/bin/env bash
# Build the claude.ai skill zip (Settings → Skills): explain/ at the zip root,
# without capture.py (Claude Code only) and without Python caches.
# Usage: bash scripts/pack.sh [out-dir]   (default: dist/)
set -euo pipefail
repo="$(cd "$(dirname "$0")/.." && pwd)"
out="${1:-$repo/dist}"
mkdir -p "$out"
out="$(cd "$out" && pwd)"
zip_path="$out/draw-it-out-explain.zip"
rm -f "$zip_path"
cd "$repo/skills"
zip -qr "$zip_path" explain -x '*__pycache__*' '*.pyc' 'explain/engine/capture.py'
echo "$zip_path"
```

**Step 4: Run test to verify it passes**
Run: `python3 -m unittest discover -s tests -p test_pack.py -v`
Expected: PASS, 1 test OK

**Step 5: Commit**
`git add -A && git commit -m "feat: pack.sh builds the claude.ai skill zip"`


### Task 15: README

**Lane:** pack

**Files:**
- Modify: `README.md` (replace the one-line file)
- Modify: `tests/test_pack.py`

**Step 1: Write the failing test**

Insert above the final `if __name__ == "__main__":` block of `tests/test_pack.py`:

```python
class Readme(unittest.TestCase):
    def test_readme_says_how_to_install_and_test(self):
        text = (REPO / "README.md").read_text(encoding="utf-8")
        for needle in ("claude plugin marketplace add nicodiansk/draw-it-out",
                       "claude plugin install draw-it-out@draw-it-out", "/draw-it-out:explain",
                       "bash scripts/pack.sh", "python3 -m unittest discover -s tests", "glitch-walk"):
            self.assertIn(needle, text)
```

**Step 2: Run test to verify it fails**
Run: `python3 -m unittest discover -s tests -p test_pack.py -v`
Expected: FAIL: 1 failure, `'claude plugin marketplace add nicodiansk/draw-it-out' not found`

**Step 3: Write minimal implementation**

Replace `README.md` with:

````markdown
# draw-it-out

Explains things as a **drawing that builds itself**, in plain words, for people who built
software with AI and can't read the code.

- **walk**: "what happens when I click Pay?" Follows the real path through your code and draws
  it, with the code behind each piece and, optionally, real screenshots.
- **sheet**: "explain this process." Turns a pipeline, an agent loop or a business flow into one
  or more animated sheets. Code is optional.

The sheet is written in your language, whatever it is.

## Install

Claude Code:

```
claude plugin marketplace add nicodiansk/draw-it-out
claude plugin install draw-it-out@draw-it-out
```

Then ask a question, or run `/draw-it-out:explain`.

claude.ai: run `bash scripts/pack.sh`, then upload `dist/draw-it-out-explain.zip` in
Settings → Skills.

Screenshots (Claude Code only, optional): `pip install playwright && python3 -m playwright install chromium`.

## How it works

Claude writes only data: a JSON file that names pieces, shapes and the lines of code behind
them. `skills/explain/engine/render.py` (Python standard library only) checks it, reads the
code from disk, and writes one HTML file. It refuses a missing file, a line range that doesn't
exist, an unknown shape, a piece with more than one sentence, more than 20 pieces on a sheet,
and a loop in the order. The shapes and fields are in `skills/explain/schema.md`.

It is read-only: it never edits your project, submits a form, signs in or pays.

## Develop

```
python3 -m unittest discover -s tests -v
```

The browser tests skip unless Playwright and Chromium (or Chrome) are installed.
After a deliberate template change: `UPDATE_SNAPSHOTS=1 python3 -m unittest discover -s tests`,
review `tests/snapshots/`, rerun.

Ideas adapted from [glitch-walk](https://github.com/Glitch-Cat-Club/glitch-skills) (MIT).
The look is the nicodiansk Zine design system.
````

**Step 4: Run test to verify it passes**
Run: `python3 -m unittest discover -s tests -v`
Expected: PASS: the full suite (this lane runs after every other lane), 63 tests OK (6 skipped without Playwright)

**Step 5: Commit**
`git add -A && git commit -m "docs: README with install, claude.ai zip and tests"`
