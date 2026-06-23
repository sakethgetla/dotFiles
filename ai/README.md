# ai/

Personal tooling for AI/agent workflows.

## Components

| Name | What it does |
|---|---|
| [`triage/`](./triage/) | Terminal-centric session triage for codex running in kitty tabs. Marks tabs with 🟢/🟡/🔴 based on per-session state. Includes a TUI dashboard. |

---

# triage

A terminal-centric session-triage UX, scoped to codex sessions running in kitty tabs.

## Why

Running ~5–10 codex sessions across kitty tabs in parallel surfaces two pain points:

1. Forgetting what a finished task was doing once it completes.
2. Manually polling every tab to see which need attention.

This is a lightweight terminal-only approach: ~2 small Python processes, no servers, no browser.

## Architecture

```
┌──────────────────────┐    writes     ┌──────────────────────┐   reads    ┌──────────────────┐
│  watcher (launchd)   │ ────────────> │  ~/.triage/          │ <─────────  │  dashboard (TUI) │
│  - kitty @ ls poll   │               │   state.json         │             │  - textual app   │
│  - lsof correlation  │               │   summaries.json     │             │  - left = list   │
│  - JSONL classifier  │               │   regen.requests     │  <─────────  │  - right = swap  │
│  - tab title marker  │               └──────────────────────┘   appends    │  - ↵ swap-to-pane│
│  - codex spark        │                                                    └──────────────────┘
│    summaries          │
└──────────────────────┘
```

- **Watcher** = single Python daemon launched by launchd. Polls `kitty @ ls` every 1.5s. Correlates kitty windows → codex PIDs via process tree → JSONL files via `lsof`. Writes atomically to `~/.triage/state.json`. Sets per-tab emoji marker in the tab title. On every `task_complete`, fires a `codex exec -m gpt-5.3-codex-spark` job (in a 2-worker thread pool) to refresh that session's one-line summary; caches the result in `~/.triage/summaries.json`.
- **State file** = `~/.triage/state.json`. Cheap to read, easy to debug with `jq`. Each session row now carries `summary`.
- **Summary cache** = `~/.triage/summaries.json`. Keyed by session JSONL path. Persists across watcher restarts so reboots don't re-spend on summaries.
- **Regen IPC** = `~/.triage/regen.requests`. Dashboard appends a session path when the user presses `s`; watcher drains-then-deletes on the next tick and submits a fresh summary job.
- **Dashboard** = textual TUI, runs in one kitty tab. Left pane is the list; right pane is a "preview slot" — pressing ↵ on a row uses `kitty @ detach-window` to swap that session into the right pane (and the previously-shown session goes back to its home tab). Pure reader of `state.json`. Stateless, kill and restart freely.

## Tab marker spec

| Marker | Meaning |
|---|---|
| 🟢 | every codex session in the tab is RUNNING (no one needs me) |
| 🟡 | mix — at least one needs me AND at least one running |
| 🔴 | every codex session needs me (no running) |
| *(none)* | no codex in that tab, or the dashboard tab itself (excluded) |

UNKNOWN (codex alive but no JSONL yet — just launched, no first prompt) counts as **needs-me** for aggregation.

### Aggregation pseudocode

```
needs_me = count(s in (NEEDS_YOU, UNKNOWN))
running  = count(s == RUNNING)

if needs_me == 0:  return 🟢
if running  == 0:  return 🔴
                   return 🟡
```

## Per-session state classification

Pure function over a JSONL tail. Rule: wall-clock idle is never a flip signal; long tool calls / big model turns must not false-positive.

| Last lifecycle event in tail | Process alive | State |
|---|---|---|
| `event_msg.payload.type == "task_complete"` | any | NEEDS_YOU |
| `event_msg.payload.type == "turn_aborted"` | any | NEEDS_YOU |
| `event_msg.payload.type == "task_started"` | yes | RUNNING |
| nothing classifiable in tail | no | NEEDS_YOU |
| nothing classifiable in tail | yes | UNKNOWN |

Codex JSONL vocabulary (verified empirically):
- `event_msg.payload.type` ∈ {`task_started`, `task_complete`, `turn_aborted`, `agent_message`, `user_message`, `token_count`, `patch_apply_end`, `context_compacted`}
- `response_item.payload.type` ∈ {`function_call`, `function_call_output`, `custom_tool_call`, `custom_tool_call_output`, `message`, `reasoning`, `tool_search_call`, `tool_search_output`}

Only `task_started` / `task_complete` / `turn_aborted` are lifecycle markers. Tool calls live on `response_item` and don't alter classification — between a `task_started` and a `task_complete` the session is RUNNING regardless of the last event being a tool call or a reasoning chunk.

## Kitty correlation strategy

1. `kitty @ ls` → JSON tree of OS-windows → tabs → windows. Each window has `pid`, `foreground_processes` (list of `{pid, cmdline, cwd}`), `tab_id`, `title`.
2. For each window, walk `foreground_processes` looking for a cmdline whose basename is `codex`.
3. For each codex PID found, `lsof -p <pid>` → find the open `.jsonl` under `~/.codex/sessions/`.
4. Read tail of each session, classify, aggregate per tab, set tab title with marker.

**Socket discovery:** `kitty.conf` uses `listen_on unix:/tmp/kitty-$KITTY_PID`. launchd-launched processes don't inherit `KITTY_LISTEN_ON`, so the watcher globs `/tmp/kitty-*` and probes each socket with `kitty @ --to <socket> ls` until one works. Caches the working socket.

**Tab title manipulation:** original (marker-stripped) title is cached per tab so it can be restored when codex exits or the watcher shuts down. Each tick strips any existing marker prefix, computes the desired marker for the current aggregate, and only calls `kitty @ set-tab-title` when the title actually differs.

## File layout

```
ai/triage/
├── triage/                Python package
│   ├── classifier.py        pure: JSONL tail → State
│   ├── codex.py             lsof correlation, process liveness, codex PID detection
│   ├── kitty.py             kitty @ wrappers + socket discovery + detach-window
│   ├── state.py             state.json schema + atomic write
│   ├── summaries.py         summaries.json cache + transcript extract + SummaryManager (codex exec)
│   ├── watcher.py           daemon: tick loop, aggregation, tab title mgmt, summary regen
│   └── dashboard.py         textual TUI (TriageApp); expandable rows
├── tests/                 25 unit tests + 5 JSONL fixtures
├── bin/
│   ├── triage               launches the dashboard
│   └── triage-watcher       launches the daemon (used by launchd)
├── launchd/com.user.triage-watcher.plist.template
├── scripts/setup            one-shot installer
└── requirements.txt         textual >= 0.60
```

## Setup

```bash
~/me/dotFiles/ai/triage/scripts/setup
# Cmd+Q kitty and reopen (allow_remote_control needs a fresh kitty)
```

The setup script:

1. Creates `.venv` and installs `textual`.
2. Renders + installs `~/Library/LaunchAgents/com.user.triage-watcher.plist`.
3. Bootstraps (or kickstarts) the launchd job.
4. Appends to `~/me/dotFiles/terminalEmulators/kitty/kitty.conf` (idempotent):
   ```
   # triage
   allow_remote_control yes
   listen_on unix:/tmp/kitty-$KITTY_PID
   ```

Idempotent — safe to re-run.

## Usage

```bash
# Dashboard (open in any kitty tab, ideally a new one):
~/me/dotFiles/ai/triage/bin/triage
```

Dashboard keys:

| Key | Action |
|---|---|
| `j` / `↓` | move down |
| `k` / `↑` | move up |
| `↵` | swap the highlighted session into the dashboard tab's right pane (and send the previous right-pane session back to its home tab). If the session is already in the dashboard tab, just focuses the window |
| `s` | force-regenerate the summary for the highlighted row (row shows `…` until the watcher's next tick picks up the result) |
| `r` | force refresh |
| `q` | quit |

Rows are sorted with NEEDS YOU first, then RUNNING. A red `●` means needs-you; green means running. Non-highlighted rows show `meta · summary truncated`; the highlighted row expands inline to show the full summary on its own line.

The dashboard tab is auto-named `triage` (via OSC sequence) so the watcher excludes it from marking.

## Operations

```bash
# tail watcher log
tail -f /tmp/triage-watcher.log

# inspect current state
cat ~/.triage/state.json | jq

# inspect what kitty sees
kitty @ ls | jq '[.[].tabs[] | {id, title, fg: [.windows[].foreground_processes[]?.cmdline[0]?]}]'

# restart the watcher (after editing watcher.py)
launchctl kickstart -k gui/$(id -u)/com.user.triage-watcher

# stop everything (restores all tab titles)
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.user.triage-watcher.plist

# tests
cd ~/me/dotFiles/ai/triage && .venv/bin/pytest tests/
```

## Splits within a tab

Kitty windows have globally unique IDs regardless of whether they're in their own tab (Cmd+T) or splits within a tab (Ctrl+Shift+Enter). The dashboard handles both:

```
                  kitty.app (OS window)
                  ├── tab 3   (Cmd+T)
                  │     ├── win 4   ← codex A
                  │     └── win 5   ← codex B  (split)
                  ├── tab 6
                  │     └── win 9   ← codex C
                  └── ...

state.json sees:                    dashboard renders:
   tab=3 win=4  codex A      →      [tab 3·w4]  ...   ← suffix because tab 3 shared
   tab=3 win=5  codex B      →      [tab 3·w5]  ...
   tab=6 win=9  codex C      →      [tab 6]     ...   ← no suffix, sole codex in tab 6

Enter on any row → kitty @ focus-window --match id:{window_id}
   → kitty switches tab AND focuses the right split. Same call either way.
```

Tab title shows the aggregate marker across all sessions in that tab (see Tab marker spec above).

## Known limitations (v1)

| Scenario | Behavior | Why |
|---|---|---|
| codex paused on plan-mode / approval / "Action Required" | tab marker stays where it was based on JSONL | codex TUI prompts don't emit JSONL events; passive reader can't see them |
| subagent codex (child of orchestrator codex) | invisible in dashboard | subagent isn't a foreground process in any kitty window, so no lsof correlation possible |
| codex in tmux / ssh / nested shells | invisible | not foreground in a kitty window |
| Claude sessions | not supported | different JSONL dialect; architecture is identical but classifier would need a second parser |
| Linux | not supported | lsof flags + launchd plist; would need a fork |
| LLM-generated summaries | none — row label is the kitty tab title | v2 candidate |

## Reference

- Classifier rule: wall-clock age is NEVER an idle trigger while a live process exists.
- Approval handling: this project keeps approvals on; codex TUI approval prompts don't emit JSONL, so paused-on-approval sessions can't be detected (see Known limitations).

## v2 candidates

- ~~LLM-generated per-session summaries (cheap model, regenerate on `task_complete`).~~ Shipped — uses `gpt-5.3-codex-spark` via `codex exec`. Whole-session transcript is sent on every regen; v2 candidate is incremental "prior summary + new turn → updated summary" to cut cost on long sessions.
- TTY scraping for approval-prompt / plan-mode detection.
- Claude session support (new classifier + JSONL parser).
- Priority signalling in the dashboard (oldest-waiting NEEDS_YOU first).
- Prune `summaries.json` of entries older than N days at watcher startup.
