# 0004 — Approval / plan-mode detection (`BLOCKED` state)

- **Tier:** 2 · **Effort:** M · **Status:** idea

## Summary

Detect when codex is paused on an approval prompt or plan-mode review and surface a new `BLOCKED` state (🟠), distinct from "task done".

## Motivation

- **Biggest blind spot** (README known-limitation #1): codex paused on "Allow command?" / plan-mode emits **no JSONL event**.
- A blocked session is classified `RUNNING` and looks busy — the most misleading failure mode.
- "Waiting on my approval" is urgent in a different way than "task complete".

## Design

- JSONL can't see TUI prompts → scrape the terminal text.
- `kitty @ get-text --match id:<window_id>` returns the visible pane buffer.
- Regex for known prompt banners: approval (`Allow command?`, `y/n`), plan-mode review, "Action Required".
- Only scrape when `classify()` says `RUNNING` (cheap: skips done/idle sessions).
- New `State.BLOCKED` overrides `RUNNING` when a prompt is matched.

```
classify(tail) == RUNNING
   → kitty get-text(window_id)
       matches approval/plan banner? → BLOCKED
       else                          → RUNNING
```

## Marker / aggregation impact

- New marker 🟠 for `BLOCKED`.
- `aggregate_marker`: `BLOCKED` counts as needs-me (like `UNKNOWN`); decide precedence vs 🟡.
- Update README marker spec + `aggregate_marker` rules.

## Touchpoints

- `kitty.py`: add `get_text(window_id)`.
- `classifier.py` (or new `tty.py`): banner regexes.
- `state.py`: add `State.BLOCKED`.
- `watcher.py`: call scrape on RUNNING sessions; thread new state through aggregation.
- `dashboard.py`: 🟠 dot + counts column.

## Effort

- Medium. New TTY-scrape path + state + marker wiring. Regexes are codex-version-fragile → keep them in one place.

## Open questions

- Throttle `get-text` (every tick vs every Nth) for cost?
- How stable are codex prompt strings across versions?
