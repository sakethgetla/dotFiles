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
    assert "--next-to" not in argv
    assert not any(str(a).startswith("--location") for a in argv)


def test_launch_command_in_tab_placement_flags(monkeypatch):
    calls = _capture(monkeypatch)
    kitty.launch_command_in_tab(5, ["codex"], next_to=42, location="after")
    argv = calls[0]
    assert "--next-to" in argv and argv[argv.index("--next-to") + 1] == "id:42"
    assert "--location=after" in argv
    # placement flags precede the positional program
    assert argv[-1] == "codex"


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


def test_neighbor_right_of_active_parses_match(monkeypatch):
    # kitty @ ls --match neighbor:right returns the matching window subtree.
    out = '[{"tabs":[{"id":1,"windows":[{"id":34}]}]}]'
    monkeypatch.setattr(kitty, "_run", lambda *a, **k: _FakeProc(out, 0))
    assert kitty.neighbor_right_of_active() == 34


def test_neighbor_right_of_active_none_on_no_match(monkeypatch):
    # rightmost pane → kitty errors "No matching windows" (nonzero returncode).
    monkeypatch.setattr(kitty, "_run", lambda *a, **k: _FakeProc("", 1))
    assert kitty.neighbor_right_of_active() is None


def test_window_is_focused():
    ls = [{"tabs": [{"id": 1, "windows": [
        {"id": 10, "is_focused": True},
        {"id": 11, "is_focused": False},
    ]}]}]
    assert kitty.window_is_focused(ls, 10) is True
    assert kitty.window_is_focused(ls, 11) is False
    assert kitty.window_is_focused(ls, 999) is False
