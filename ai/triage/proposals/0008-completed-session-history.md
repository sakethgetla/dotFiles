# 0008 — Browse & resume previously-run sessions

- **Tier:** 3 · **Effort:** M · **Status:** in-progress

> Reframed from the original "append-only completed-session log". The shipped direction is a **history browser + resume**: the dashboard lists previously-run codex sessions (read directly from `~/.codex/sessions`) and resumes a chosen one into the right pane. The append-only `history.jsonl` log (original design, preserved below under "Alternative") is now optional/complementary, not required.

## Summary

When triage is open — including when **nothing is live** in kitty — show recent previously-run codex sessions in the dashboard list, below a `── history ──` divider. Press Enter on a history row to `codex resume <uuid>` it into the dashboard tab's right pane.

## Motivation

- Addresses README pain point #1: "Forgetting what a finished task was doing once it completes."
- The dashboard previously only showed live sessions; once a tab closed, the work was gone from view.
- Lets you reopen a finished/closed session without hunting for it manually.

## Design (shipped direction)

- **History source:** scan `~/.codex/sessions/YYYY/MM/DD/rollout-<ts>-<uuid>.jsonl` directly — newest date dirs first, hard cap K=40, first-line `session_meta` per file (UUID, cwd, branch, start ts). Bounded so the ~2600-file tree is never fully enumerated. (`triage/history.py`.)
- **Labels (no LLM on browse):** reuse `summaries.json` cache by path if present; else `<repo>·<branch> — <first user prompt>`; else `<basename> — (no preview)`.
- **List:** live rows (needs/running) → `── history ──` divider → history rows (always inline, no toggle). Dedup history against live paths. Throttled rescan (~5s); re-filter against live paths every refresh.
- **Resume (Enter on a history row):** launch `codex resume <uuid>` (`--cwd` the recorded dir if it still exists, `--hold` to surface errors) into a new right pane.
  - If the right pane already holds a **live** codex → detach it to its **own new tab** (preserved, never closed).
  - If it holds the placeholder shell → close it.
  - The resumed pane is a live codex; the next watcher tick promotes it to a live row and dedup drops it from history.
- **Data model:** `SessionRow` gains defaulted `kind` / `session_id` / `cwd`; historical rows are sentinel-valued (`window_id=-1`) and in-memory only (never written to `state.json`).

## Touchpoints

- New: `triage/history.py`, `tests/test_history.py`.
- Edit: `triage/state.py` (fields), `triage/kitty.py` (`launch_command_in_tab`, `close_window`, `detach_window` → `"new"` target), `triage/dashboard.py` (history block, `kind` header branch, Enter branch + `_resume_historical`).

## Alternative (original idea, optional)

Persist a one-line record per completed session to `~/.triage/history.jsonl` (`{ts, session_path, tab_title, summary}`), deduped by `(session_path, source_last_event_at)`. Complementary to the live scan — useful as a durable "what got done today" log that survives session-file pruning — but not required for browse-and-resume. Open questions if pursued: log at `task_complete` then backfill the summary, and a rotation/pruning policy.
