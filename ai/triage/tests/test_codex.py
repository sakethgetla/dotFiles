from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from triage import codex


class _FakeProc:
    def __init__(self, stdout: str, returncode: int = 0):
        self.stdout = stdout
        self.returncode = returncode


def _lsof_stdout(paths: list[str]) -> str:
    # jsonl_for_pid only reads lines starting with "n" (lsof -Fn name records).
    return "\n".join(f"n{p}" for p in paths) + "\n"


def _patch(monkeypatch, paths: list[str], subagents: set[str] = frozenset()):
    sd = str(codex.CODEX_SESSIONS_DIR)
    full = [f"{sd}/2026/06/24/{name}" for name in paths]
    sub_full = {f"{sd}/2026/06/24/{name}" for name in subagents}
    monkeypatch.setattr(
        codex.subprocess, "run", lambda *a, **k: _FakeProc(_lsof_stdout(full))
    )
    monkeypatch.setattr(codex, "_is_subagent_rollout", lambda p: p in sub_full)
    return full


def test_jsonl_for_pid_none_when_no_session_files(monkeypatch):
    monkeypatch.setattr(codex.subprocess, "run", lambda *a, **k: _FakeProc("n/tmp/x\n"))
    assert codex.jsonl_for_pid(123) is None


def test_jsonl_for_pid_single_candidate(monkeypatch):
    full = _patch(monkeypatch, ["rollout-2026-06-24T10-00-00-019ef702-aaaa.jsonl"])
    assert codex.jsonl_for_pid(123) == full[0]


def test_jsonl_for_pid_prefers_newest_created_fork_over_parent(monkeypatch):
    # Parent (702, older) + fork (840, newer) both open. Must return the fork,
    # regardless of lsof ordering — selection is by creation order, not mtime.
    parent = "rollout-2026-06-24T10-23-09-019ef702-63f6.jsonl"
    fork = "rollout-2026-06-24T16-10-55-019ef840-c81a.jsonl"
    full = _patch(monkeypatch, [fork, parent])  # parent listed last on purpose
    assert codex.jsonl_for_pid(123).endswith(fork)


def test_jsonl_for_pid_excludes_subagent_rollout(monkeypatch):
    # Own session (older) + a newer sub-agent rollout open. Sub-agent excluded,
    # so the own session wins even though the sub-agent file is newer-created.
    own = "rollout-2026-06-24T15-00-00-019ef833-9fc8.jsonl"
    sub = "rollout-2026-06-24T16-21-05-019ef84a-174c.jsonl"
    _patch(monkeypatch, [sub, own], subagents={sub})
    assert codex.jsonl_for_pid(123).endswith(own)


def test_jsonl_for_pid_all_subagents_falls_back(monkeypatch):
    # Degenerate: every open rollout is a sub-agent. Don't return None — fall
    # back to the full set and pick newest-created.
    a = "rollout-2026-06-24T16-00-00-019ef000-1111.jsonl"
    b = "rollout-2026-06-24T16-21-05-019ef84a-174c.jsonl"
    _patch(monkeypatch, [a, b], subagents={a, b})
    assert codex.jsonl_for_pid(123).endswith(b)
