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
  every request that is not a read, in popups too, plus WebSockets and service workers, so a
  click on Pay shows the page but sends nothing. Never ask the user to sign in for a
  screenshot. Exit 3 means Playwright is missing: go on without screenshots. Exit 1 means that
  page couldn't be captured (the line says why): go on without that screenshot.
- **claude.ai**: the screenshots the user uploaded, if any.
- Otherwise none: the sheet is code only.

Each shot names the piece it shows (`piece`) and a short `tag`.

## 5. Render and show

`"mode": "walk"`, the user's question as `title`. Render and show as SKILL.md says.
