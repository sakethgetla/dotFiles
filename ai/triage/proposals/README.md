# triage proposals

Feature proposals for the triage app. One file per proposal. Keep this index in sync.

## Convention

- Filename: `NNNN-kebab-title.md` (zero-padded, monotonic).
- Each proposal has: **Summary · Motivation · Design · Touchpoints · Effort · Status**.
- Status ∈ `idea` · `accepted` · `in-progress` · `shipped` · `icebox` · `dropped`.

## Index

| # | Proposal | Tier | Effort | Status |
|---|---|---|---|---|
| [0001](./0001-needs-you-notifications.md) | Notify on `NEEDS_YOU` flip | 1 | S | idea |
| [0002](./0002-prune-stale-summaries.md) | Prune stale summary cache | 1 | S | shipped |
| [0003](./0003-prioritize-needs-you-by-age.md) | Sort NEEDS_YOU by oldest-waiting | 1 | S | idea |
| [0004](./0004-approval-plan-mode-detection.md) | Approval / plan-mode detection (`BLOCKED`) | 2 | M | idea |
| [0005](./0005-claude-session-support.md) | Claude session support | 2 | M | idea |
| [0006](./0006-incremental-summaries.md) | Incremental summaries | 2 | M | idea |
| [0007](./0007-jump-to-next-needs-you.md) | Jump-to-next-needs-you hotkey | 1 | S | idea |
| [0008](./0008-completed-session-history.md) | Browse & resume previously-run sessions | 3 | M | in-progress |
| [0009](./0009-swap-restore-true-home-tab.md) | Swap returns displaced pane to its true home tab (bug) | 1 | S | idea |
| [0010](./0010-fix-launch-window-tab-matcher.md) | Fix `launch_window_in_tab` tab matcher (bug) | 1 | S | idea |
| [0011](./0011-harden-original-titles-lifecycle.md) | Harden `_original_titles` lifecycle (bug) | 1 | S | idea |

## Icebox

- Per-session activity sparkline in the dashboard.
- Linux fork (`/proc` + systemd user unit instead of `lsof` + launchd).
- Priority signalling colours beyond red/green.

## Tiers

- **Tier 1** — high value, low effort. Closes the core notify/prioritise/cleanup loop.
- **Tier 2** — high value, medium effort. Correctness + reach (blind spots, Claude, cost).
- **Tier 3** — bigger bets.
