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
