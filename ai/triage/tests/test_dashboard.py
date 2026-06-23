from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from textual.widgets import ListView

from triage import dashboard
from triage.dashboard import TriageApp
from triage.state import DashboardState, SessionRow, State


def _hist_row(tab_title: str) -> SessionRow:
    return SessionRow(
        tab_id=-1, window_id=-1, tab_title=tab_title, session_path="/s/a.jsonl",
        codex_pid=-1, state=State.NEEDS_YOU, last_event_type=None,
        last_event_at="2026-06-20T05:00:00.000Z", summary="lbl",
        kind="historical", session_id="UUID", cwd="/x/myrepo",
    )


def _live_row(summary: str = "s", tab_title: str = "proj") -> SessionRow:
    return SessionRow(
        tab_id=3, window_id=4, tab_title=tab_title, session_path="/s/b.jsonl",
        codex_pid=9, state=State.RUNNING, last_event_type="task_started",
        last_event_at="2026-06-20T05:00:00.000Z", summary=summary,
    )


def _patch_dashboard_io(monkeypatch, tmp_path, rows: list[SessionRow]) -> Path:
    regen = tmp_path / "regen.requests"
    monkeypatch.setattr(dashboard.kitty, "ls", lambda: [])
    monkeypatch.setattr(dashboard.state_module, "read_state", lambda: DashboardState("now", 1, rows))
    monkeypatch.setattr(dashboard.history, "build_history_rows", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard.summaries, "load_cache", lambda: {})
    monkeypatch.setattr(dashboard, "REGEN_REQUESTS_PATH", regen)
    return regen


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def test_date_bucket_today():
    assert dashboard._date_bucket(_iso(datetime.now())) == "today"


def test_date_bucket_yesterday():
    assert dashboard._date_bucket(_iso(datetime.now() - timedelta(days=1))) == "yesterday"


def test_date_bucket_older():
    assert dashboard._date_bucket(_iso(datetime.now() - timedelta(days=5))) == "older"


def test_date_bucket_none_and_malformed():
    assert dashboard._date_bucket(None) == "older"
    assert dashboard._date_bucket("not-a-date") == "older"


def test_format_header_historical_includes_branch_and_glyph():
    header = TriageApp._format_header(_hist_row("myrepo·main"), {})
    assert "○" in header                 # hollow glyph distinguishes from live ●
    assert "●" not in header
    assert "[myrepo·main]" in header      # repo·branch in the bracket
    assert "ran" in header and "ago" in header


def test_format_header_live_unchanged():
    live = _live_row()
    header = TriageApp._format_header(live, {3: 1})
    assert "●" in header and "○" not in header
    assert "tab 3" in header


def test_historical_resume_uses_plain_codex(monkeypatch):
    app = TriageApp()
    app._self_tab_id = 5
    row = _hist_row("myrepo")
    row.cwd = "/Users/sakethgetla/yellowbox/main"
    captured = {}

    monkeypatch.setattr(app, "_current_right_pane", lambda: None)
    monkeypatch.setattr(app, "_plain_codex_command", lambda: "/plain/codex")
    monkeypatch.setattr(dashboard.os.path, "isdir", lambda p: True)
    monkeypatch.setattr(dashboard.kitty, "focus_window", lambda window_id: None)

    def launch(tab_id, cmd_args, cwd=None, hold=False, copy_env=False):
        captured.update(
            tab_id=tab_id, cmd_args=cmd_args, cwd=cwd, hold=hold, copy_env=copy_env
        )
        return 99

    monkeypatch.setattr(dashboard.kitty, "launch_command_in_tab", launch)

    app._resume_historical(row)

    assert captured["tab_id"] == 5
    assert captured["cmd_args"] == ["/plain/codex", "resume", "UUID"]
    assert captured["cwd"] == "/Users/sakethgetla/yellowbox/main"
    assert captured["hold"] is True
    assert captured["copy_env"] is True


def test_new_session_launches_codex_on_right(monkeypatch):
    app = TriageApp()
    app._self_tab_id = 5
    captured = {}

    monkeypatch.setattr(app, "_current_right_pane", lambda: None)
    monkeypatch.setattr(app, "_codex_command", lambda: "/native/codex")
    monkeypatch.setattr(app, "_new_session_cwd", lambda: "/Users/sakethgetla/yellowbox")
    monkeypatch.setattr(dashboard.kitty, "focus_window", lambda window_id: captured.update(focused=window_id))

    def launch(tab_id, cmd_args, cwd=None, hold=False, copy_env=False):
        captured.update(
            tab_id=tab_id, cmd_args=cmd_args, cwd=cwd, hold=hold, copy_env=copy_env
        )
        return 99

    monkeypatch.setattr(dashboard.kitty, "launch_command_in_tab", launch)

    app.action_new_session()

    assert captured["tab_id"] == 5
    assert captured["cmd_args"] == ["/native/codex"]
    assert captured["cwd"] == "/Users/sakethgetla/yellowbox"
    assert captured["hold"] is True
    assert captured["copy_env"] is True
    assert captured["focused"] == 99


def test_refresh_updates_existing_row_in_place(monkeypatch, tmp_path):
    _patch_dashboard_io(monkeypatch, tmp_path, [_live_row()])

    async def run():
        app = TriageApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            lv = app.query_one("#sessions", ListView)
            first = lv.children[0]
            await app.refresh_data()
            assert lv.children[0] is first

    asyncio.run(run())


def test_regen_summary_escapes_markup_text(monkeypatch, tmp_path):
    regen = _patch_dashboard_io(
        monkeypatch,
        tmp_path,
        [_live_row(summary="summary with [brackets]", tab_title="proj [main]")],
    )

    async def run():
        app = TriageApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("s")
            await pilot.pause()

    asyncio.run(run())
    assert regen.read_text() == "/s/b.jsonl\n"
