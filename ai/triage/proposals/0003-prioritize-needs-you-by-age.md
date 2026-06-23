# 0003 — Sort NEEDS_YOU by oldest-waiting

- **Tier:** 1 · **Effort:** S · **Status:** idea

## Summary

Within the NEEDS_YOU group, sort rows oldest-waiting-first so the most-neglected session surfaces at the top.

## Motivation

- Today `ordered = needs + running` preserves arbitrary insertion order inside each group.
- When several sessions need you, you want the one that has been waiting longest first.

## Design

- In `dashboard.refresh_data()`, sort `needs` by `last_event_at` ascending (oldest first).
- `running` can stay as-is, or sort by most-recently-active.

```
needs.sort(key=lambda s: s.last_event_at or "")   # oldest task_complete first
ordered = needs + running
```

## Touchpoints

- `dashboard.py`: `refresh_data()` only. Pure reader change — no watcher/state impact.

## Effort

- Small. One sort line. Pairs naturally with [0007](./0007-jump-to-next-needs-you.md).

## Open questions

- Tie-break for equal/`None` timestamps (fall back to tab/window id)?
