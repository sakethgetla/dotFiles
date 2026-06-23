# 0010 — Fix `launch_window_in_tab` tab matcher

- **Tier:** 1 · **Effort:** S · **Status:** idea

> Found by verification-squad review. Latent correctness bug — works today only by accident of the active-tab fallback.

## Summary

`kitty.launch_window_in_tab(tab_id)` **and** `kitty.launch_command_in_tab(tab_id, …)` spawn a pane with `kitty @ launch --match id:{tab_id}`, but kitty's `--match id:` matches **window** ids, not **tab** ids. The new pane lands in the right place today only because kitty falls back to the active tab — and the dashboard's tab happens to be active whenever these run.

> Update (post-review): the bug has since spread. The resume/new-session feature added `launch_command_in_tab`, which copies the same wrong matcher. There are now **two functions and three call sites** affected.

## Motivation

- It works now purely by luck of timing, not by intent.
- Two concrete ways it bites:
  1. If a *window* id ever equals the target tab id and that window is the active/foreground one, kitty splits next to **that window** (potentially in a different tab) instead of the intended tab.
  2. Any future caller that invokes this when the target tab is **not** active gets the pane in the wrong tab silently.

## Root cause

`kitty.py` — both launch helpers pass the tab id to `--match id:` (`launch_window_in_tab` ≈ line 142, `launch_command_in_tab` ≈ line 175):

```python
def launch_window_in_tab(tab_id: int) -> int | None:
    r = _run("launch", "--type=window", "--match", f"id:{tab_id}", ...)   # ← id: matches a WINDOW

def launch_command_in_tab(tab_id, cmd_args, ...):
    args = ["launch", "--type=window", "--match", f"id:{tab_id}", ...]    # ← same bug
```

kitty `--match id:N` resolves `N` against window ids. There is no window-vs-tab namespacing, so a tab id is interpreted as a window id; no match → kitty uses the active window/tab.

Call sites — all three pass `self._self_tab_id` (the dashboard's own tab) and all run while that tab is active, which is why the active-tab fallback masks the bug:
- `dashboard.py` `_init_layout` ≈ line 170 → `launch_window_in_tab(self._self_tab_id)`
- `dashboard.py` `action_new_session` ≈ line 380 → `launch_command_in_tab(self._self_tab_id, …)`
- `dashboard.py` `_resume_historical` ≈ line 404 → `launch_command_in_tab(self._self_tab_id, …)`

`self._self_window_id` (a real window guaranteed to be in `_self_tab_id`) is resolved before every one of these, so a proper anchor is already on hand.

## Design

Anchor both launches on a **window** known to be in the target tab, instead of on the tab id. All three call sites already hold such a window: `self._self_window_id`.

- Retarget both helpers to take an anchor window id:

```python
def launch_window_next_to(window_id: int) -> int | None:
    r = _run("launch", "--type=window", "--match", f"id:{window_id}", timeout=3)
    ...

def launch_command_next_to(window_id: int, cmd_args, cwd=None, hold=False) -> int | None:
    args = ["launch", "--type=window", "--match", f"id:{window_id}", ...]
    ...
```

- Update the three call sites to pass `self._self_window_id` instead of `self._self_tab_id`:

```python
# _init_layout
kitty.launch_window_next_to(self._self_window_id)
# action_new_session / _resume_historical
kitty.launch_command_next_to(self._self_window_id, [...], cwd=cwd, hold=True)
```

Deterministic regardless of which tab is active; removes the tab-id-as-window-id confusion entirely.

```
before: launch --match id:{tab_id}      → relies on active-tab fallback
after : launch --match id:{self_window} → always splits inside the dashboard's tab
```

## Touchpoints

- `kitty.py`: retarget `launch_window_in_tab` and `launch_command_in_tab` to anchor on a window id.
- `dashboard.py`: three call sites (`_init_layout` ≈170, `action_new_session` ≈380, `_resume_historical` ≈404) pass `self._self_window_id`.

## Effort

- Small. Two signatures + three call sites. `_self_window_id` is already resolved before each call.

## Verification

- Open the dashboard alone in a tab → confirm the spawned right pane appears **in that tab** (`kitty @ ls`).
- Exercise new-session (`action_new_session`) and resume-historical (`_resume_historical`) → confirm each lands in the dashboard tab.
- Contrive a layout where a window id equals the dashboard's tab id with that window focused in another tab → confirm the pane still lands in the dashboard tab (would mis-split under the old matcher).

## Open questions

- Keep the old names as thin aliases? Not needed — all callers are internal and updated together.
