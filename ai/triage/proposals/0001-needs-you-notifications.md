# 0001 — Notify on `NEEDS_YOU` flip

- **Tier:** 1 · **Effort:** S · **Status:** idea

## Summary

Fire a desktop notification (or kitty bell) the moment a session transitions into `NEEDS_YOU`.

## Motivation

- The whole point of triage is "tell me when to look".
- Today you still have to glance at the tab markers to notice a flip.
- A push signal closes the loop so you can ignore the terminal until pinged.

## Design

- In `watcher.tick()`, the per-tab/session states are already computed each tick.
- Keep a `prev_states: dict[session_path, State]` across ticks (like `last_markers`).
- On any `RUNNING|UNKNOWN → NEEDS_YOU` edge, emit one notification.
- Debounce: only notify on the edge, never while already `NEEDS_YOU`.
- Notification body = `summary` if cached, else tab title.

```
prev      now         action
RUNNING → NEEDS_YOU    notify("<tab>: <summary>")
NEEDS_YOU → NEEDS_YOU  (silent)
RUNNING → RUNNING      (silent)
```

## Touchpoints

- `watcher.py`: thread `prev_states` through `tick()`; add `_notify()` helper.
- macOS: `terminal-notifier` if present, else `osascript -e 'display notification …'`, else kitty bell (`\a`).

## Effort

- Small. ~30 lines, no new files. No new state file needed (in-memory across ticks).

## Open questions

- Per-session vs per-tab notification when a tab has multiple sessions?
- Opt-out env var / quiet hours?
