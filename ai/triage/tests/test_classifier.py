from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from triage.classifier import classify, tail_jsonl
from triage.state import State

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> list[dict]:
    return [
        json.loads(line)
        for line in (FIXTURES / name).read_text().splitlines()
        if line.strip()
    ]


def test_task_complete_alive_is_needs_you():
    state, ev, _ = classify(load("task_complete.jsonl"), process_alive=True)
    assert state == State.NEEDS_YOU
    assert ev == "task_complete"


def test_task_complete_dead_is_needs_you():
    state, _, _ = classify(load("task_complete.jsonl"), process_alive=False)
    assert state == State.NEEDS_YOU


def test_mid_tool_alive_is_running():
    state, _, _ = classify(load("mid_tool.jsonl"), process_alive=True)
    assert state == State.RUNNING


def test_mid_tool_dead_is_needs_you():
    state, _, _ = classify(load("mid_tool.jsonl"), process_alive=False)
    assert state == State.NEEDS_YOU


def test_task_started_alive_is_running():
    state, ev, _ = classify(load("task_started.jsonl"), process_alive=True)
    assert state == State.RUNNING
    assert ev == "task_started"


def test_task_started_dead_is_needs_you():
    state, _, _ = classify(load("task_started.jsonl"), process_alive=False)
    assert state == State.NEEDS_YOU


def test_turn_aborted_is_needs_you():
    state, ev, _ = classify(load("turn_aborted.jsonl"), process_alive=True)
    assert state == State.NEEDS_YOU
    assert ev == "turn_aborted"


def test_multi_turn_running():
    state, ev, _ = classify(load("multi_turn_running.jsonl"), process_alive=True)
    assert state == State.RUNNING
    assert ev == "task_started"


def test_empty_alive_is_unknown():
    state, _, _ = classify([], process_alive=True)
    assert state == State.UNKNOWN


def test_empty_dead_is_needs_you():
    state, _, _ = classify([], process_alive=False)
    assert state == State.NEEDS_YOU


def test_tail_jsonl_handles_missing_file(tmp_path):
    assert tail_jsonl(tmp_path / "nope.jsonl") == []


def test_tail_jsonl_reads_lines(tmp_path):
    p = tmp_path / "f.jsonl"
    p.write_text('{"a":1}\n{"b":2}\n{"c":3}\n')
    out = tail_jsonl(p, max_lines=2)
    assert out == [{"b": 2}, {"c": 3}]


def test_tail_jsonl_tolerates_garbage(tmp_path):
    p = tmp_path / "f.jsonl"
    p.write_text('{"a":1}\nnot json\n{"c":3}\n')
    out = tail_jsonl(p)
    assert out == [{"a": 1}, {"c": 3}]
