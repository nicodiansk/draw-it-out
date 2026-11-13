# ATLAS — draw-it-out

Last updated: 2026-11-13

## Where to Look

| I want to... | Open | Why |
|--------------|------|-----|
| Change when the skill triggers or how it picks walk vs sheet | `skills/explain/SKILL.md` | Frontmatter `description` is the trigger; body routes to the mode file |
| Change the walk procedure (questions, reading code, screenshots) | `skills/explain/walk.md` | Steps 1–5 of a walk, shape table for code |
| Change the sheet procedure (process drawings) | `skills/explain/sheet.md` | Steps 1–4 of a sheet, shape table for processes |
| See or change the JSON the model writes | `skills/explain/schema.md` | Fields, shapes, `ui` keys; kept in step with `render.py` by `tests/test_skill_docs.py` |
| Add or change a validation rule | `skills/explain/engine/render.py` | `check_sheet` (per sheet) and `build` (whole document) |
| Change how code is read from disk | `skills/explain/engine/render.py` | `inside` refuses paths outside `--root`; `extract` reads the lines |
| Add a language's built-in UI words | `skills/explain/engine/render.py` | `UI` dict (`en`, `it`); other langs must send a full `ui` object |
| Change the look (Zine tokens, shapes, layout, motion) | `skills/explain/engine/template.html` | CSS at the top, renderer JS in the second `<script>` |
| Fix layout of columns, flow arrows, error arrows | `skills/explain/engine/template.html` | `.dio-slot` (a column plus its incoming arrow) / `.dio-join` CSS; `routeBacks` draws the error arrows |
| Change the stop-motion build-in or replay/← → controls | `skills/explain/engine/template.html` | `show` / `run` / `stop` near the end |
| Change what a screenshot run may do | `skills/explain/engine/capture.py` | `allow_request` is the network rule; `guard` applies it to the whole context (popups, WebSockets, no service workers) |
| Change what goes into the claude.ai zip | `scripts/pack.sh` | `zip -x` excludes `capture.py` and caches |
| Change the README images (banner, screenshots, self-diagram) | `docs/readme/` + `scripts/readme_images.py` | `hero.html` and `how-it-works.json` are the sources; the script renders and shoots them as JPEG |
| See a complete valid input | `skills/explain/examples/walk.json`, `sheet.json` | Walk over the `shop/` mini-app; Italian two-sheet process |
| Understand why it is built this way | `docs/plans/2026-11-13-draw-it-out-design.md` | Agreed design (brainstorm) |
| See every task, decision and Review Focus | `docs/plans/2026-11-13-draw-it-out.md` | Implementation plan (15 tasks, 5 lanes) |

## Entry Points

| File | Role | Starts |
|------|------|--------|
| `skills/explain/SKILL.md` | Skill (`/draw-it-out:explain`, model-invocable) | The walk or sheet procedure |
| `skills/explain/engine/render.py` | CLI: `render.py <json> --root <project> --out <html>` | Validation → code extraction → one HTML file; exit 1 prints `field → problem → how to fix` |
| `skills/explain/engine/capture.py` | CLI (Claude Code only): `capture.py <localhost url> --out <png> [--click] [--wait]` | Playwright screenshot; exit 1 (one line) when the page can't be captured, 3 when Playwright is missing |
| `scripts/pack.sh` | Bash: `bash scripts/pack.sh [out-dir]` | Builds `draw-it-out-explain.zip` (default `dist/`) |
| `.claude-plugin/plugin.json` | Plugin manifest | Name `draw-it-out`, version `0.1.0` |
| `.claude-plugin/marketplace.json` | Marketplace manifest | Lists this repo (`source: ./`), no version |

## Module Map

| Directory | One-line purpose | Key files |
|-----------|------------------|-----------|
| `.claude-plugin/` | Plugin + marketplace manifests, plugin icon | `plugin.json`, `marketplace.json`, `icon.png` |
| `skills/explain/` | The one skill, two modes | `SKILL.md`, `walk.md`, `sheet.md`, `schema.md` |
| `skills/explain/engine/` | Renderer, HTML template, screenshotter | `render.py`, `template.html`, `capture.py` |
| `skills/explain/examples/` | Valid inputs + the tiny project they point at | `walk.json`, `sheet.json`, `shop/` |
| `skills/explain/examples/shop/` | Mini checkout app the walk example reads code from | `api/pay.js`, `lib/card.js`, `lib/db.js`, `app/pay-button.js`, `shots/checkout.svg` |
| `tests/` | stdlib `unittest` suite (79 tests) | `helpers.py`, `test_render.py`, `test_browser.py`, `test_capture.py`, `test_snapshots.py` |
| `tests/snapshots/` | Expected HTML of the two examples | `walk.html`, `sheet.html` |
| `scripts/` | Packaging, README images | `pack.sh`, `readme_images.py` |
| `docs/readme/` | README graphics and their sources | `hero.html`, `how-it-works.json`, `*.jpg` |
| `docs/plans/` | Design and implementation plan | `2026-11-13-draw-it-out-design.md`, `2026-11-13-draw-it-out.md` |

## Key Symbols

(Heuristic, not AST-exhaustive.)

| Symbol | File:line-range | Kind |
|--------|-----------------|------|
| `SHAPES` | `skills/explain/engine/render.py:18` | const: `you ai check thing tested look` |
| `MAX_PIECES` / `MAX_TITLE_WORDS` / `MAX_LABEL_WORDS` / `MAX_TAG_WORDS` | `skills/explain/engine/render.py:19-22` | const: 20 / 9 / 3 / 6 |
| `UI` / `UI_KEYS` | `skills/explain/engine/render.py:29-50` | const: built-in page words (`en`, `it`) |
| `Problems` | `skills/explain/engine/render.py:53-55` | class: collected `field → problem → fix` lines |
| `one_sentence` | `skills/explain/engine/render.py:58-65` | function: a stop before a lowercase word ("e.g. the") doesn't end a sentence |
| `parse_lines` / `parse_focus` | `skills/explain/engine/render.py:68-86` | function: focus checked against the range before expanding |
| `find_cycle` | `skills/explain/engine/render.py:89-111` | function: loop in `after` |
| `ranks` | `skills/explain/engine/render.py:114-124` | function: column of each piece |
| `title_lines` | `skills/explain/engine/render.py:127-137` | function: 2–3 lines of ≤3 words |
| `inside` | `skills/explain/engine/render.py:140-145` | function: refuses paths outside `--root` |
| `extract` | `skills/explain/engine/render.py:148-179` | function: reads code lines from disk, split on `\n` only |
| `listed` | `skills/explain/engine/render.py:192-198` | function: a field that must be a list |
| `check_sheet` | `skills/explain/engine/render.py:201-287` | function: shapes, sentences, limit, cycles, arrows, gaps |
| `build` | `skills/explain/engine/render.py:290-370` | function: whole document → page data |
| `render_html` | `skills/explain/engine/render.py:373-379` | function: fills `__LANG__` `__TITLE__` `__DATA__`, escapes `<` |
| `main` | `skills/explain/engine/render.py:382-401` | function: CLI |
| `allow_request` | `skills/explain/engine/capture.py:25-27` | function: only GET/HEAD to localhost |
| `is_local` | `skills/explain/engine/capture.py:20-22` | function |
| `Step` / `parse` | `skills/explain/engine/capture.py:30-53` |
| `guard` / `shoot` | `skills/explain/engine/capture.py:56-78` | functions: context-wide route + WebSocket block; one capture | class / function: ordered `--click` / `--wait` |
| `main` (capture) | `skills/explain/engine/capture.py:81-104` | function: falls back to `channel="chrome"`; Playwright errors → one line, exit 1 |
| `dio-data` script block | `skills/explain/engine/template.html:135` | JSON payload the page draws |
| `DIE` / `DOODLES` | `skills/explain/engine/template.html:140-143` | const: die SVG; Zine doodles (asterisk-pink, sparkle-paper, cross-paper) |
| `codePanel` / `pieceEl` | `skills/explain/engine/template.html:168-256` | JS functions: code panel, one piece |
| `routeBacks` | `skills/explain/engine/template.html:195-243` | JS: error arrows under the row (side by side) or along the right edge (stacked); redrawn on resize |
| sheet drawing loop | `skills/explain/engine/template.html:257-348` | JS: columns, joins, error arrows, unsure, legend, StageBar |
| `show` / `stop` / `run` | `skills/explain/engine/template.html:350-371` | JS: build-in by `data-step` (story order), replay, ← → keys |
| `render` (test helper) | `tests/helpers.py:12-16` | function: runs `render.py` as the skill does |

## Integration Points

| System | Config key | Path |
|--------|------------|------|
| Google Fonts (Archivo Black, Inter, Space Mono) | link in `<head>` | `skills/explain/engine/template.html:7-9` |
| Playwright for Python (optional) | `pip install playwright`; system Chrome via `channel="chrome"` | `skills/explain/engine/capture.py`, `tests/test_browser.py` |
| Claude Code marketplace | `claude plugin marketplace add nicodiansk/draw-it-out` | `.claude-plugin/marketplace.json` |
| claude.ai skill upload | zip from `scripts/pack.sh` | `dist/draw-it-out-explain.zip` (gitignored) |

## Conventions & Gotchas

- Code reaches the page only via `extract`: the JSON holds `{file, lines, focus}`, never code text.
- Code paths resolve under `--root`; screenshot paths resolve next to the JSON (project stays read-only).
- `arrows[]` is only the error path and must point back to an earlier column; forward arrows come from `after`.
- More than 20 pieces → `sheets[]` replaces top-level `pieces`/`arrows`/`unsure`; ids unique across sheets.
- `render_html` escapes `<` as `\u003c` so piece text can't close the `<script>`; page always has exactly two script blocks.
- Snapshots: any template change fails `test_snapshots.py`; rerun with `UPDATE_SNAPSHOTS=1`, review, commit.
- Browser tests and the capture smoke test skip without Playwright; in the cloud sandbox Playwright's bundled Chromium is missing and system Chrome is used.
- `tests/test_pack.py` packs a temp copy of `scripts/` + `skills/` with a planted `__pycache__/x.pyc`, so the real repo stays clean.
- README images are JPEG on purpose: the film grain makes PNGs 2–6 MB. Shoot with a viewport as tall as the page, not `full_page` (the grain layer is `position: fixed`).
- Zine is dark only (no light theme); Zine visual rules come from the "nicodiansk Zine" design-system artifact.
- Build-in order is the `data-step` number, not page order: a column's incoming arrow and an error arrow's line, tag and caption share one step.
- Error-arrow labels: on the arrow (`.dio-back__tag`) side by side; listed under the sheet (`.dio-backs`) when stacked under 700px (`.is-stacked`).
- The shot tag sits above the screenshot (`order: -1`, tilts from its bottom-left), never over it.

<!-- 📌-prefixed lines are manual notes, preserved across atlas updates -->
<!-- atlas-hash:e7b16e8142d5 -->
