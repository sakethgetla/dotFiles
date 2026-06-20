from __future__ import annotations

import glob
import json
import logging
import os
import subprocess
from typing import Iterator

log = logging.getLogger("triage.kitty")

_socket_cache: str | None = None


def _candidate_sockets() -> list[str]:
    """Return possible kitty remote-control sockets, prioritised."""
    out: list[str] = []
    env_sock = os.environ.get("KITTY_LISTEN_ON")
    if env_sock:
        out.append(env_sock)
    for path in sorted(glob.glob("/tmp/kitty-*")):
        if os.path.exists(path):
            out.append(f"unix:{path}")
    return out


def _probe(socket: str) -> bool:
    try:
        r = subprocess.run(
            ["kitty", "@", "--to", socket, "ls"],
            capture_output=True,
            timeout=2,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
    return r.returncode == 0


def _resolve_socket() -> str | None:
    global _socket_cache
    if _socket_cache and _probe(_socket_cache):
        return _socket_cache
    for sock in _candidate_sockets():
        if _probe(sock):
            _socket_cache = sock
            log.info("using kitty socket %s", sock)
            return sock
    _socket_cache = None
    return None


def _run(*args: str, timeout: float = 3.0) -> subprocess.CompletedProcess[str]:
    sock = _resolve_socket()
    cmd = ["kitty", "@"]
    if sock:
        cmd.extend(["--to", sock])
    cmd.extend(args)
    return subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout, check=False
    )


def ls() -> list[dict]:
    """Return `kitty @ ls` JSON output (list of OS windows)."""
    try:
        r = _run("ls")
    except subprocess.TimeoutExpired:
        return []
    if r.returncode != 0 or not r.stdout.strip():
        return []
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return []


def set_tab_color(tab_id: int, active_bg: str, inactive_bg: str) -> None:
    try:
        _run(
            "set-tab-color",
            "--match",
            f"id:{tab_id}",
            f"active_bg={active_bg}",
            f"inactive_bg={inactive_bg}",
            timeout=2,
        )
    except subprocess.TimeoutExpired:
        pass


def set_tab_title(tab_id: int, title: str) -> None:
    try:
        _run("set-tab-title", "--match", f"id:{tab_id}", title, timeout=2)
    except subprocess.TimeoutExpired:
        pass


def focus_tab(tab_id: int) -> None:
    try:
        _run("focus-tab", "--match", f"id:{tab_id}", timeout=2)
    except subprocess.TimeoutExpired:
        pass


def focus_window(window_id: int) -> None:
    """Focus a specific kitty window (works across tabs and within splits)."""
    try:
        _run("focus-window", "--match", f"id:{window_id}", timeout=2)
    except subprocess.TimeoutExpired:
        pass


def iter_tab_windows(
    ls_output: list[dict],
) -> Iterator[tuple[int, str, int, int, list[dict]]]:
    """Yield (tab_id, tab_title, window_id, window_pid, foreground_processes)."""
    for osw in ls_output:
        for tab in osw.get("tabs") or []:
            tab_id = tab.get("id")
            tab_title = tab.get("title", "") or ""
            if not isinstance(tab_id, int):
                continue
            for window in tab.get("windows") or []:
                window_id = window.get("id")
                window_pid = window.get("pid")
                if not isinstance(window_id, int):
                    continue
                yield (
                    tab_id,
                    tab_title,
                    window_id,
                    window_pid if isinstance(window_pid, int) else -1,
                    window.get("foreground_processes") or [],
                )
