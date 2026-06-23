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


def detach_window(window_id: int, target_tab: int | str) -> None:
    """Move a kitty window (pane) into another tab.

    target_tab is an existing tab id (int) → --target-tab id:M, or the literal
    "new" → --target-tab new, which moves the window into a brand-new tab.

    kitty @ detach-window --match id:N --target-tab (id:M | new)
    """
    target = "new" if target_tab == "new" else f"id:{target_tab}"
    try:
        _run(
            "detach-window",
            "--match", f"id:{window_id}",
            "--target-tab", target,
            timeout=2,
        )
    except subprocess.TimeoutExpired:
        pass


def close_window(window_id: int) -> None:
    """Close a kitty window. A non-matching id is a harmless no-op."""
    try:
        _run("close-window", "--match", f"id:{window_id}", timeout=2)
    except subprocess.TimeoutExpired:
        pass


def launch_window_in_tab(tab_id: int) -> int | None:
    """Spawn a new pane (default shell) in the given tab; return its window id."""
    try:
        r = _run(
            "launch",
            "--type=window",
            "--match", f"id:{tab_id}",
            timeout=3,
        )
    except subprocess.TimeoutExpired:
        return None
    if r.returncode != 0:
        return None
    try:
        return int(r.stdout.strip())
    except ValueError:
        return None


def launch_command_in_tab(
    tab_id: int,
    cmd_args: list[str],
    cwd: str | None = None,
    hold: bool = False,
    copy_env: bool = False,
) -> int | None:
    """Spawn a new pane in the given tab running cmd_args; return its window id.

    hold=True keeps the pane open after the command exits (so an error from the
    launched program stays visible instead of the pane vanishing). cwd sets the
    working directory. copy_env=True copies the active window's environment into
    the new pane — kitty otherwise execs the program directly under the server's
    env (no shell, so .zshrc exports like $EDITOR are absent). The program and
    its args are passed positionally last.

    kitty @ launch --type=window --match id:N [--hold] [--copy-env] [--cwd D] <prog> [args...]
    """
    args = ["launch", "--type=window", "--match", f"id:{tab_id}"]
    if hold:
        args.append("--hold")
    if copy_env:
        args.append("--copy-env")
    if cwd:
        args.extend(["--cwd", cwd])
    args.extend(cmd_args)
    try:
        r = _run(*args, timeout=3)
    except subprocess.TimeoutExpired:
        return None
    if r.returncode != 0:
        return None
    try:
        return int(r.stdout.strip())
    except ValueError:
        return None


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
