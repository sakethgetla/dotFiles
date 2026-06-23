# 0009 — Swap returns displaced pane to its TRUE home tab

- **Tier:** 1 · **Effort:** S · **Status:** idea

> Found by verification-squad review of the pane-swap feature. Confirmed behavioral bug, not a crash.

## Summary

When you press `↵` to swap a session into the dashboard's right pane, the session currently occupying that pane is sent to the **wrong tab**. It goes to the *incoming* session's home tab instead of its own original home tab.

## Motivation

- README promises: *"pressing ↵ … uses `kitty @ detach-window` to swap that session into the right pane (and the previously-shown session goes back to **its home tab**)."*
- Actual behaviour: the previously-shown session goes to **the incoming session's** home tab.
- Effect is "A and P trade places": correct only when the displaced pane `P` originally came from the same tab the incoming session `A` lives in. In the cross-tab case `P` is dumped into an unrelated tab and is orphaned from where it started.

## Root cause

`dashboard.py` `on_list_view_selected` (≈ line 415):

```python
if item.row.kind == "historical":          # resume path — handled separately
    self._resume_historical(item.row)
    return
window_id  = item.row.window_id            # A, the incoming session
target_tab = self._tab_for_window(window_id)   # A's CURRENT tab
...
right_pane = self._current_right_pane()    # P, the previous occupant
if right_pane is not None:
    kitty.detach_window(right_pane, target_tab)   # ← sends P to A's tab, not P's home
kitty.detach_window(window_id, self._self_tab_id) # bring A into dashboard tab
kitty.focus_window(window_id)
```

`target_tab` is the tab `A` is being pulled *out* of. Passing it as the destination for `P` is the bug — the code has no memory of where `P` came from.

```
state before ↵ on A:
   dashboard tab: [dashboard | P]      P's real home = tab Tp
   tab Ta:        [A]

after (current/buggy):
   dashboard tab: [dashboard | A]
   tab Ta:        [P]        ← P lands in A's old tab, NOT Tp
   tab Tp:        [] (P never returns home)

after (desired):
   dashboard tab: [dashboard | A]
   tab Tp:        [P]        ← P back to its real home
   tab Ta:        [] (A moved out)
```

## Design

Remember each session's home tab at the moment it is swapped *into* the pane, and use that on the way out.

- Add `self._pane_home: dict[int, int] = {}` (window_id → original home tab_id) to `TriageApp.__init__` (≈ line 120, alongside `_pending_regens`).
- In `on_list_view_selected`, in the live-session swap branch (after the `kind == "historical"` early-return ≈ line 419), before bringing `A` in, record `self._pane_home[window_id] = target_tab`.
- Note: `_resume_historical` / `action_new_session` also call `_replace_right_pane`, which detaches the prior live codex to its own new tab — if home-tab fidelity matters there too, thread `_pane_home` through `_replace_right_pane`. Out of scope for the core swap bug but worth a glance.
- When evicting `P`, send it to `self._pane_home.pop(P, fallback)`; fall back to `target_tab` (current behaviour) only if `P`'s home is unknown (e.g. dashboard restarted since `P` was swapped in).

```python
right_pane = self._current_right_pane()
if right_pane is not None:
    home = self._pane_home.pop(right_pane, target_tab)   # P's real home, else fallback
    kitty.detach_window(right_pane, home)
self._pane_home[window_id] = target_tab                  # remember A's home for next eviction
kitty.detach_window(window_id, self._self_tab_id)
kitty.focus_window(window_id)
```

Edge cases:
- `P`'s home tab may have been closed (it was `P`'s only window). kitty silently no-ops a detach to a dead tab id — `P` then stays in the dashboard tab. Acceptable; optionally fall back to spawning a fresh tab, but that is scope creep.
- Dashboard restart loses `_pane_home` (in-memory). First eviction after restart falls back to the old behaviour for that one window. Acceptable.

## Touchpoints

- `dashboard.py`: `__init__` (one dict), `on_list_view_selected` (record on swap-in, look up on evict). No watcher/state/kitty-wrapper change.

## Effort

- Small. ~6 lines. Pure dashboard-local state.

## Verification

- Two sessions A (tab Ta) and B (tab Tb) in different tabs; swap A in, then swap B in → A must return to Ta (not Tb). Confirm via `kitty @ ls` that A's window id is back under tab Ta.
- Regression: when A and the previous occupant share a tab, behaviour is unchanged.

## Open questions

- If `P`'s home tab was closed, prefer (a) leave `P` in the dashboard tab, or (b) create a new tab for it? (Default: a.)
