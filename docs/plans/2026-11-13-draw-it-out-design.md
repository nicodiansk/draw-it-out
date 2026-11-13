# draw-it-out — design

Date: 2026-11-13 · Status: agreed in brainstorm, ready for story/plan

## Purpose

A Claude Code plugin (also packaged as a claude.ai skill zip) that explains things as a
**drawing that builds itself**, in the Zine visual language (design system "nicodiansk Zine",
its Diagram kit). Two modes, one skill:

- **walk** — "what happens when I click Pay?": follows the real path through the user's own
  code and draws it, with the code behind each piece and optional real screenshots.
- **sheet** — "explain this process": turns a process (a pipeline, an agent loop, a business
  flow) into one or more animated sheets. Code is optional.

Audience: vibe coders, people who built software with AI and can't read the code. Plain words,
every term explained the first time, no jargon. The sheet is written in the language of the
person asking, whatever it is.

Starting point: Glitch-Cat-Club/glitch-skills (`glitch-walk`, MIT). Kept: a rigid schema, a
build step that refuses bad data, code read from files and never retyped, "never describe what
you didn't see". Dropped: uv, Chrome as a hard requirement, `--do "<javascript>"`, screenshots
as the only evidence, no plugin manifest, no claude.ai path.

## Distribution

- GitHub repo with `.claude-plugin/plugin.json` + `marketplace.json` for Claude Code.
- `scripts/pack.sh` builds a zip of the skill folder for claude.ai (Settings → Skills).
- Not aimed at the claude.ai plugin directory for v1, so the skill may ship scripts.
- Plugin `name` is `draw-it-out` and never changes: it sets the command namespace.

## Structure

One skill with two modes. On claude.ai each skill is a separate zip that can't see the others'
folders, so two skills would each need a copy of the engine.

```
.claude-plugin/plugin.json, marketplace.json
skills/explain/
  SKILL.md          trigger + routing: walk or sheet; reads only that mode's file
  walk.md           walk procedure
  sheet.md          sheet procedure
  schema.md         the shape vocabulary, fields, limits
  engine/
    render.py       stdlib only: validate → extract code → write one HTML file
    template.html   Zine tokens, Google Fonts, JS renderer, steps() motion
    capture.py      Claude Code only, optional: Playwright screenshots of localhost
  examples/         one complete walk.json and one sheet.json
tests/              renderer tests (not in the zip)
scripts/pack.sh     builds the claude.ai zip
```

Command: `/draw-it-out:explain`.

## Flow

**walk**
1. Ask at most three questions, one at a time: what you do (the click or command), where it
   starts, what you expect to see at the end.
2. Read the real path in the code: entry → handler → checks → stored data → response. Only
   files actually opened enter the JSON.
3. Screenshots: in Claude Code, only if the app runs locally (`capture.py`). On claude.ai, the
   ones the user uploads. Otherwise none — the sheet is code only.
4. Write `walk.json` → `render.py` → `walk.html` → publish as an Artifact or open the file →
   a 2–3 line summary.

**sheet**: the same steps, with the user's description or a document as the source. Code is
optional. Above ~20 pieces it splits into several sheets, each with a StageBar.

## Engine: JSON + fixed renderer

The model writes only data. `render.py` is the only way code enters the page: the JSON says
`{"file": "app/api/pay.ts", "lines": "12-30"}` and the script reads those lines from disk.

### Shape vocabulary (Zine Diagram kit, mapped to a vibe coder's code)

| Shape | In a walk it means |
|---|---|
| mustard pill | **you**: the click, the command, the wait |
| pink box with a die | an **AI call** in your code (different answer each time) |
| teal diamond | a **check** (if, validation, permission: same answer every time) |
| paper box | a **thing**: a file, a request, a database row |
| paper block with lego studs | a piece **covered by tests** |
| dashed pink arrow | the **error path**: where you go back when a check fails, one step |
| mustard outline on ink | **look here**: the one result that matters |
| dashed box | **unsure**: a gap declared in `unsure[]` ("didn't see where the email leaves") |

### Fields

`title`, `lang`, `pieces[]` (shape, one-sentence text, optional `code: {file, lines}`,
`after`), `arrows[]`, `shots[]`, `unsure[]`.

### `render.py` refuses when

- a file is missing or the lines don't exist;
- a shape is outside the vocabulary;
- a piece's text is longer than one sentence;
- a sheet has more than 20 pieces;
- `after` makes a cycle.

It exits non-zero with a list of `field → problem → how to fix`. The model fixes at most three
times, then tells the user what is missing.

## Rendering

- **Layout**: `render.py` ranks pieces by `after` into columns, left to right. Error arrows go
  back one step, below the row, dashed pink. Under 700px columns become rows top to bottom; no
  horizontal scroll at 390px.
- **Build-in**: pieces pop in with `steps()`, about 0.5s apart, in story order, then hold.
  Controls: **▶ replay** and **← →** to step one piece at a time. Under
  `prefers-reduced-motion` everything shows at once.
- **Code**: tap a piece to open a `coal` panel below, Space Mono, `file:lines`, line numbers,
  key lines highlighted. The text is exactly what `render.py` extracted.
- **Screenshots**: a "what you see" strip above the sheet, mustard tags (tilted) pointing to
  the linked piece.
- **Zine kit**: SheetLabel top right ("Tavola 01", localised), the legend always on the first
  sheet, StageBar at the bottom when there are several sheets, film grain, the doodle SVGs (2–4
  around the title, never over text), hard shadows, alternating tilt.
- **Theme**: Zine dark only, explicit body background. Fonts from Google Fonts (Archivo Black,
  Space Mono, Inter) with Impact / monospace fallbacks offline.
- **Title**: the user's question, uppercase, 2–3 lines of at most three words, one accent per
  line (paper / teal / pink).
- Output: one self-contained HTML file.

## Safety

Read-only: never edits the project, never submits forms, never signs in, never pays.
`capture.py` opens only `localhost` and accepts only declared clicks and waits. No arbitrary JS.

## Testing (stdlib only)

- one test per refusal rule;
- code extraction exact, line by line;
- HTML snapshot of the examples;
- Playwright smoke test: renders the examples, checks the piece count, no overflow at 390px,
  reduced motion shows everything.

## Out of v1 (YAGNI)

Editing the sheet in the page, PNG/PPTX export, a light theme, design systems other than Zine,
follow-up questions, the claude.ai plugin directory.

## Licence notes

Ideas adapted from glitch-walk (MIT): keep its licence notice in `NOTICE` if any text or code is
copied or adapted. Zine tokens and doodles are the author's own design system.
