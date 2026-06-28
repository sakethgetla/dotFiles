from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

CODEX_SESSIONS_DIR = Path.home() / ".codex" / "sessions"


def _is_subagent_rollout(path: str) -> bool:
    """True if a rollout's first session_meta marks it as a sub-agent session.

    Codex stamps lineage at payload.source.subagent.thread_spawn.parent_thread_id.
    Reads only the first JSONL line. Inlined here (not imported from history.py,
    which already imports this module) to avoid a circular import.
    """
    try:
        with open(path, "r", errors="replace") as f:
            ev = json.loads(f.readline())
    except (OSError, json.JSONDecodeError, ValueError):
        return False
    payload = ev.get("payload") or {}
    src = payload.get("source")
    sub = src.get("subagent") if isinstance(src, dict) else None
    spawn = sub.get("thread_spawn") if isinstance(sub, dict) else None
    return isinstance(spawn, dict) and bool(spawn.get("parent_thread_id"))


def find_codex_in_foreground(foreground_processes: list[dict]) -> int | None:
    """Return the PID of a codex process in the given kitty foreground tree."""
    for p in foreground_processes:
        cmdline = p.get("cmdline") or []
        if not cmdline:
            continue
        prog = os.path.basename(cmdline[0])
        if prog == "codex":
            pid = p.get("pid")
            if isinstance(pid, int):
                return pid
    return None


def jsonl_for_pid(pid: int) -> str | None:
    """Find the codex session JSONL the given PID has open (via lsof)."""
    try:
        out = subprocess.run(
            ["lsof", "-p", str(pid), "-Fn"],
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None

    sessions_prefix = str(CODEX_SESSIONS_DIR)
    candidates: list[str] = []
    for line in out.stdout.splitlines():
        if not line.startswith("n"):
            continue
        path = line[1:]
        if path.startswith(sessions_prefix) and path.endswith(".jsonl"):
            candidates.append(path)
    candidates = list(dict.fromkeys(candidates))  # de-dupe (one fd entry per file)
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    # A codex process holds several rollouts open at once: after a fork it keeps
    # the parent file open alongside the fork, and it transiently holds sub-agent
    # rollouts while sub-agents run. Pick by creation order (rollout filenames and
    # ids are monotonic), not mtime — after a fork the pane continues in the
    # newest-created session, and creation order is stable against the parent's
    # mtime churn from another pane. Exclude sub-agent rollouts first.
    pool = [p for p in candidates if not _is_subagent_rollout(p)] or candidates
    return max(pool, key=os.path.basename)


def process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True
