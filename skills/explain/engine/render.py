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
