# 0011 — Harden `_original_titles` lifecycle

- **Tier:** 1 · **Effort:** S · **Status:** idea

> Found by verification-squad review. Low severity / largely self-healing — defensive hardening, not a confirmed normal-operation failure. Filed for completeness.

## Summary

The watcher caches each marked tab's pre-marker title in a module-level dict `_original_titles` so it can restore titles on shutdown. The dict is in-memory only and pruned on a single path, which leaves a couple of thin edge cases where a tab can briefly keep a stale emoji marker or a stale cached title is held longer than needed.

## Motivation

- In normal threaded operation the cache is consistent: the restore loop pops entries when a marked tab loses its codex (`watcher.py` ≈ line 160), and `restore_all_titles()` clears it on graceful shutdown.
- Two thin gaps remain:
  1. **Unclean watcher death** (SIGKILL / crash / launchd hard kill) never runs `restore_all_titles()` (only SIGTERM/SIGINT do). Tabs keep their 🟢/🟡/🔴 marker until the next watcher process happens to re-process that tab. It self-heals (`_strip_marker` removes any existing prefix before recomputing), but there is a window where titles show a stale marker with no live watcher behind it.
  2. **Per-tab staleness**: `_original_titles` only ever grows or is overwritten per tick; an entry for a tab that vanished between ticks is removed only if it was in `last_markers`. Harmless today, but it is global mutable state with one prune path — fragile against future refactors of the tick loop.

## Root cause

`watcher.py`:

```python
_original_titles: dict[int, str] = {}          # module-global, in-memory

# set when a marker is applied (≈150):
_original_titles[tab_id] = original

# pruned only here (≈160), keyed off the PREVIOUS tick's markers:
for tab_id in last_markers:
    if tab_id not in new_markers:
        original = _original_titles.pop(tab_id, None)
        if original is not None:
            kitty.set_tab_title(tab_id, original)

# cleared only on graceful shutdown (≈182):
def restore_all_titles(): ...
```

## Design

Two small, independent hardening steps (do either or both):

1. **Self-heal stale markers on startup.** On watcher start, before the first tick, strip any marker prefix from every tab title kitty currently reports. This guarantees a clean slate even after an unclean prior death.

   ```
   on start:
     for tab in kitty.ls():
        stripped = _strip_marker(title)
        if stripped != title: kitty.set_tab_title(tab_id, stripped)
   ```

2. **Prune defensively each tick.** After computing `new_markers`, drop any `_original_titles` key that is neither in `new_markers` nor a live tab this tick, so the dict can never accumulate entries for tabs that disappeared without passing through the `last_markers` path.

   ```
   live = set(tab_states) | set(new_markers)
   for tab_id in list(_original_titles):
       if tab_id not in live:
           _original_titles.pop(tab_id, None)
   ```

Optionally, fold `_original_titles` into the tick's local scope or a small `TitleManager` object instead of a module global, so its lifecycle is explicit — but that is a larger refactor than the bug warrants.

## Touchpoints

- `watcher.py`: a startup strip pass in `main()` (step 1) and/or a prune block in `tick()` (step 2).

## Effort

- Small. Each step is a handful of lines. No state-file or dashboard impact.

## Verification

- `kill -9` the watcher while tabs are marked, restart → confirm markers are cleaned within the first tick (and immediately with step 1).
- Run many ticks with tabs gaining/losing codex sessions → confirm `_original_titles` size tracks only currently-marked tabs.

## Open questions

- Is the startup strip pass (step 1) enough on its own to make step 2 unnecessary? (Likely yes for the user-visible symptom; step 2 is pure internal hygiene.)
