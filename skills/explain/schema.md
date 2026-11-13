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
