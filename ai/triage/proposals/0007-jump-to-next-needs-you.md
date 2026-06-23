# 0007 — Jump-to-next-needs-you hotkey

- **Tier:** 1 · **Effort:** S · **Status:** idea

## Summary

A `n` key that moves the cursor to the next `NEEDS_YOU` row (wrapping), so you can clear the queue without scanning.

## Motivation

- With NEEDS_YOU sorted to the top ([0003](./0003-prioritize-needs-you-by-age.md)), `n` lets you walk the queue: `n` → ↵ swap → handle → `n`.
- Keyboard-only triage loop, no eyeballing the list.

## Design

- New binding `Binding("n", "next_needs", "next")`.
- From current index, find the next `SessionItem` whose `row.state == NEEDS_YOU`; wrap to top; set `lv.index`.

```
action_next_needs:
   start = lv.index + 1
   scan children from start, wrap → first NEEDS_YOU
   lv.index = found
```

## Touchpoints

- `dashboard.py`: one binding + one action method. No watcher/state impact.

## Effort

- Small. ~15 lines.

## Open questions

- Should `N` (shift) go to previous?
