from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from triage.state import DashboardState, SessionRow, State, read_state, write_state


def _live_row() -> SessionRow:
    return SessionRow(
        tab_id=3, window_id=4, tab_title="proj", session_path="/s/a.jsonl",
        codex_pid=999, state=State.RUNNING, last_event_type="task_started",
        last_event_at="2026-06-21T10:00:00Z", summary="topic — status",
    )


def test_live_row_roundtrip_includes_defaults(tmp_path):
    p = tmp_path / "state.json"
    write_state(DashboardState("2026-06-21T10:00:00Z", 1, [_live_row()]), p)
    ds = read_state(p)
    assert ds is not None
    row = ds.sessions[0]
    assert row == _live_row()                # equality covers the new defaulted fields
    assert row.kind == "live" and row.session_id is None and row.cwd is None


def test_title_roundtrips(tmp_path):
    p = tmp_path / "state.json"
    row = _live_row()
    row.title = "Fix SCIM mapping"
    write_state(DashboardState("t", 1, [row]), p)
    assert read_state(p).sessions[0].title == "Fix SCIM mapping"


def test_read_state_tolerates_missing_new_keys(tmp_path):
    # Simulate a state.json written before the new fields existed.
    p = tmp_path / "state.json"
    p.write_text(json.dumps({
        "generated_at": "t", "watcher_pid": 7,
        "sessions": [{
            "tab_id": 1, "window_id": 2, "tab_title": "x", "session_path": "/s/b.jsonl",
            "codex_pid": 8, "state": "needs_you",
            "last_event_type": "task_complete", "last_event_at": "t2", "summary": None,
        }],
    }))
    ds = read_state(p)
    assert ds is not None
    row = ds.sessions[0]
    assert row.kind == "live"
    assert row.session_id is None
    assert row.cwd is None
    assert row.state == State.NEEDS_YOU
