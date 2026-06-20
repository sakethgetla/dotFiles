from __future__ import annotations

import os
import subprocess
from pathlib import Path

CODEX_SESSIONS_DIR = Path.home() / ".codex" / "sessions"


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
    candidates: list[tuple[float, str]] = []
    for line in out.stdout.splitlines():
        if not line.startswith("n"):
            continue
        path = line[1:]
        if path.startswith(sessions_prefix) and path.endswith(".jsonl"):
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                continue
            candidates.append((mtime, path))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


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
