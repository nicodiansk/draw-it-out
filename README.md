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
