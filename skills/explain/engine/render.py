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
