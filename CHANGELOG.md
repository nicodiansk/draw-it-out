# Changelog

All notable changes to draw-it-out. The version lives in `.claude-plugin/plugin.json`.

## 0.1.0 — 2026-11-13

First release.

- **One skill, two modes.** `walk` follows a click or a command through the user's own code;
  `sheet` draws any process. Command: `/draw-it-out:explain`.
- **Renderer** (`render.py`, Python standard library only): validates the JSON the model writes,
  reads code lines from disk, refuses bad data with one `field → problem → how to fix` line per
  problem, and writes one self-contained HTML file.
- **Page** in the Zine look: a drawing that builds itself in story order, with replay and
  step controls, a code panel per piece, a legend, error arrows routed back to their target,
  several sheets with a stage bar, and a stacked layout under 700px. Reduced motion shows
  everything at once.
- **Languages:** English and Italian built in; any other language with a translated `ui`.
- **Screenshots** (`capture.py`, Claude Code only, optional): localhost only, `GET`/`HEAD` only,
  popups, WebSockets and service workers blocked.
- **Distribution:** Claude Code marketplace in this repo; `scripts/pack.sh` builds the claude.ai
  skill zip.
