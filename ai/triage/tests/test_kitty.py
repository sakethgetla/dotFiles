from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from triage import kitty


class _FakeProc:
    def __init__(self, stdout="123", returncode=0):
        self.stdout = stdout
        self.returncode = returncode


def _capture(monkeypatch, stdout="123", returncode=0):
    calls: list[tuple] = []

    def fake_run(*args, timeout=3.0):
        calls.append(args)
        return _FakeProc(stdout, returncode)

    monkeypatch.setattr(kitty, "_run", fake_run)
    return calls


def test_launch_command_in_tab_builds_argv(monkeypatch):
    calls = _capture(monkeypatch)
    win = kitty.launch_command_in_tab(
        5, ["codex", "resume", "UUID-X"], cwd="/work/dir", hold=True
    )
    assert win == 123
    argv = calls[0]
    assert argv[0] == "launch"
    assert "--hold" in argv
    assert "--cwd" in argv and argv[argv.index("--cwd") + 1] == "/work/dir"
    assert "--match" in argv and argv[argv.index("--match") + 1] == "id:5"
    # program + args passed positionally, last and in order
    assert argv[-3:] == ("codex", "resume", "UUID-X")


def test_launch_command_in_tab_omits_optional_flags(monkeypatch):
    calls = _capture(monkeypatch)
    kitty.launch_command_in_tab(5, ["codex", "resume", "U"])
    argv = calls[0]
    assert "--hold" not in argv
    assert "--cwd" not in argv


def test_launch_command_in_tab_bad_stdout_returns_none(monkeypatch):
    _capture(monkeypatch, stdout="not-an-int")
    assert kitty.launch_command_in_tab(5, ["x"]) is None


def test_launch_command_in_tab_nonzero_returns_none(monkeypatch):
    _capture(monkeypatch, returncode=1)
    assert kitty.launch_command_in_tab(5, ["x"]) is None


def test_detach_window_to_existing_tab(monkeypatch):
    calls = _capture(monkeypatch)
    kitty.detach_window(7, 12)
    argv = calls[0]
    assert argv[0] == "detach-window"
    assert argv[argv.index("--target-tab") + 1] == "id:12"


def test_detach_window_to_new_tab(monkeypatch):
    calls = _capture(monkeypatch)
    kitty.detach_window(7, "new")
    argv = calls[0]
    assert argv[argv.index("--target-tab") + 1] == "new"


def test_close_window_builds_argv(monkeypatch):
    calls = _capture(monkeypatch)
    kitty.close_window(9)
    argv = calls[0]
    assert argv[0] == "close-window"
    assert argv[argv.index("--match") + 1] == "id:9"
