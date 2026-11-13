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
