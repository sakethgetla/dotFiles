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


def test_format_header_historical_glyph_and_age_only():
    header = TriageApp._format_header(_hist_row("myrepo·main"))
    assert "○" in header                 # hollow glyph distinguishes from live ●
    assert "●" not in header
    assert "myrepo·main" not in header    # tab title is no longer rendered
    assert "ran" in header and "ago" in header


def test_format_header_live_dot_and_age_only():
    live = _live_row()
    header = TriageApp._format_header(live)
    assert "●" in header and "○" not in header
    assert "tab" not in header            # tab number is no longer rendered
    assert "proj" not in header           # tab title is no longer rendered
    assert "last ev" in header


def test_format_header_renders_bold_title():
    live = _live_row()
    live.title = "Fix SCIM mapping"
    header = TriageApp._format_header(live)
    assert "[bold]Fix SCIM mapping[/]" in header
    # No title → no bold title segment.
    assert "[bold]" not in TriageApp._format_header(_live_row())


def test_format_header_historical_renders_title():
    hist = _hist_row("myrepo·main")
    hist.title = "Past task headline"
    header = TriageApp._format_header(hist)
    assert "[bold]Past task headline[/]" in header
    assert "○" in header and "ran" in header  # still a historical row


def test_format_header_escapes_title_markup():
    live = _live_row()
    live.title = "fix [red] tag"
    header = TriageApp._format_header(live)
    assert r"fix \[red] tag" in header


def test_format_header_marked_prepends_glyph():
    from triage.marks import MARK_GLYPH
    assert MARK_GLYPH not in TriageApp._format_header(_live_row(), marked=False)
    assert TriageApp._format_header(_live_row(), marked=True).startswith(MARK_GLYPH)
    assert TriageApp._format_header(_hist_row("r"), marked=True).startswith(MARK_GLYPH)


def test_format_header_active_prepends_arrow():
    assert "▶" not in TriageApp._format_header(_live_row(), active=False)
    assert "▶" in TriageApp._format_header(_live_row(), active=True)
    assert "▶" in TriageApp._format_header(_hist_row("r"), active=True)


def _ls_focused(self_win: int, focused: bool):
    return [{"tabs": [{"id": 5, "windows": [
        {"id": self_win, "is_focused": focused},
    ]}]}]


def test_sync_right_pane_queries_neighbor_when_focused(monkeypatch):
    app = TriageApp()
    app._self_window_id = 10
    monkeypatch.setattr(dashboard.kitty, "ls", lambda: _ls_focused(10, True))
    monkeypatch.setattr(dashboard.kitty, "neighbor_right_of_active", lambda: 11)
    assert app._sync_right_pane() == 11
    assert app._active_chat_win == 11  # cached


def test_sync_right_pane_uses_cache_when_unfocused(monkeypatch):
    app = TriageApp()
    app._self_window_id = 10
    app._active_chat_win = 11  # last known
    monkeypatch.setattr(dashboard.kitty, "ls", lambda: _ls_focused(10, False))
    # neighbor must NOT be consulted while unfocused (relative to wrong window).
    monkeypatch.setattr(dashboard.kitty, "neighbor_right_of_active",
                        lambda: (_ for _ in ()).throw(AssertionError("queried while blurred")))
    assert app._sync_right_pane() == 11


def test_sync_right_pane_none_without_layout(monkeypatch):
    app = TriageApp()
    app._self_window_id = None
    monkeypatch.setattr(dashboard.kitty, "ls", lambda: _ls_focused(10, True))
    assert app._sync_right_pane() is None


def test_replace_right_pane_detaches_codex(monkeypatch):
    app = TriageApp()
    calls = []
    monkeypatch.setattr(dashboard.kitty, "detach_window", lambda w, t: calls.append(("detach", w, t)))
    monkeypatch.setattr(dashboard.kitty, "close_window", lambda w: calls.append(("close", w)))
    app._replace_right_pane(new_win=99, right=7, right_is_codex=True)
    assert calls == [("detach", 7, "new")]  # live chat preserved in a new tab


def test_replace_right_pane_closes_own_placeholder(monkeypatch):
    app = TriageApp()
    app._placeholder_win = 7
    calls = []
    monkeypatch.setattr(dashboard.kitty, "detach_window", lambda w, t: calls.append(("detach", w, t)))
    monkeypatch.setattr(dashboard.kitty, "close_window", lambda w: calls.append(("close", w)))
    app._replace_right_pane(new_win=99, right=7, right_is_codex=False)
    assert calls == [("close", 7)]


def test_replace_right_pane_leaves_user_app_untouched(monkeypatch):
    app = TriageApp()
    app._placeholder_win = 3  # not the right pane
    calls = []
    monkeypatch.setattr(dashboard.kitty, "detach_window", lambda w, t: calls.append(("detach", w, t)))
    monkeypatch.setattr(dashboard.kitty, "close_window", lambda w: calls.append(("close", w)))
    app._replace_right_pane(new_win=99, right=7, right_is_codex=False)
    assert calls == []  # a pane we don't own is never moved or closed


def test_historical_resume_uses_plain_codex(monkeypatch):
    app = TriageApp()
    app._self_tab_id = 5
    row = _hist_row("myrepo")
    row.cwd = "/Users/sakethgetla/yellowbox/main"
    captured = {}

    app._self_window_id = 10
    monkeypatch.setattr(app, "_sync_right_pane", lambda: None)
    monkeypatch.setattr(app, "_plain_codex_command", lambda: "/plain/codex")
    monkeypatch.setattr(dashboard.os.path, "isdir", lambda p: True)
    monkeypatch.setattr(dashboard.kitty, "focus_window", lambda window_id: None)

    def launch(tab_id, cmd_args, cwd=None, hold=False, copy_env=False,
               next_to=None, location=None):
        captured.update(
            tab_id=tab_id, cmd_args=cmd_args, cwd=cwd, hold=hold, copy_env=copy_env,
            next_to=next_to, location=location,
        )
        return 99

    monkeypatch.setattr(dashboard.kitty, "launch_command_in_tab", launch)

    app._resume_historical(row)

    assert captured["tab_id"] == 5
    assert captured["cmd_args"] == ["/plain/codex", "resume", "UUID"]
    assert captured["cwd"] == "/Users/sakethgetla/yellowbox/main"
    assert captured["hold"] is True
    assert captured["copy_env"] is True
    # new chat lands directly right of the dashboard window
    assert captured["next_to"] == 10
    assert captured["location"] == "after"


def test_new_session_launches_codex_on_right(monkeypatch):
    app = TriageApp()
    app._self_tab_id = 5
    captured = {}

    app._self_window_id = 10
    monkeypatch.setattr(app, "_sync_right_pane", lambda: None)
    monkeypatch.setattr(app, "_codex_command", lambda: "/native/codex")
    monkeypatch.setattr(app, "_new_session_cwd", lambda: "/Users/sakethgetla/yellowbox")
    monkeypatch.setattr(dashboard.kitty, "focus_window", lambda window_id: captured.update(focused=window_id))

    def launch(tab_id, cmd_args, cwd=None, hold=False, copy_env=False,
               next_to=None, location=None):
        captured.update(
            tab_id=tab_id, cmd_args=cmd_args, cwd=cwd, hold=hold, copy_env=copy_env,
            next_to=next_to, location=location,
        )
        return 99

    monkeypatch.setattr(dashboard.kitty, "launch_command_in_tab", launch)

    app.action_new_session()

    assert captured["tab_id"] == 5
    assert captured["cmd_args"] == ["/native/codex"]
    assert captured["cwd"] == "/Users/sakethgetla/yellowbox"
    assert captured["hold"] is True
    assert captured["copy_env"] is True
    assert captured["next_to"] == 10
    assert captured["location"] == "after"
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


def _needs_row(path: str, last_event_at: str, tab_id: int) -> SessionRow:
    return SessionRow(
        tab_id=tab_id, window_id=tab_id, tab_title=f"t{tab_id}", session_path=path,
        codex_pid=tab_id, state=State.NEEDS_YOU, last_event_type="task_complete",
        last_event_at=last_event_at, summary="s",
    )


def test_needs_you_sorted_newest_first(monkeypatch, tmp_path):
    # Out-of-order input; expect descending last_event_at (least time waiting top).
    rows = [
        _needs_row("/s/old.jsonl", "2026-06-20T01:00:00.000Z", 1),
        _needs_row("/s/new.jsonl", "2026-06-20T05:00:00.000Z", 2),
        _needs_row("/s/mid.jsonl", "2026-06-20T03:00:00.000Z", 3),
    ]
    _patch_dashboard_io(monkeypatch, tmp_path, rows)

    async def run():
        app = TriageApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            lv = app.query_one("#sessions", ListView)
            paths = [c.row.session_path for c in lv.children]
            assert paths == ["/s/new.jsonl", "/s/mid.jsonl", "/s/old.jsonl"]

    asyncio.run(run())


def test_active_right_pane_chat_pinned_first(monkeypatch, tmp_path):
    # "old" would normally sort last; pinning it as the open chat moves it first,
    # with the remaining rows keeping their newest-first order.
    rows = [
        _needs_row("/s/old.jsonl", "2026-06-20T01:00:00.000Z", 1),
        _needs_row("/s/new.jsonl", "2026-06-20T05:00:00.000Z", 2),
        _needs_row("/s/mid.jsonl", "2026-06-20T03:00:00.000Z", 3),
    ]
    _patch_dashboard_io(monkeypatch, tmp_path, rows)

    async def run():
        app = TriageApp()
        app._self_window_id = 99
        # "/s/old.jsonl" lives in window 1 (_needs_row sets window_id == tab_id);
        # it's the dashboard's right-neighbor.
        monkeypatch.setattr(app, "_sync_right_pane", lambda: 1)
        async with app.run_test() as pilot:
            await pilot.pause()
            lv = app.query_one("#sessions", ListView)
            paths = [c.row.session_path for c in lv.children]
            assert paths == ["/s/old.jsonl", "/s/new.jsonl", "/s/mid.jsonl"]
            assert "▶" in lv.children[0]._last_header

    asyncio.run(run())


def test_active_marker_unique_when_forks_share_path(monkeypatch, tmp_path):
    # Two forks transiently resolve to the same jsonl but live in different
    # panes (windows 21, 22). Only the right-pane window (21) may be marked.
    rows = [
        _needs_row("/s/same.jsonl", "2026-06-20T05:00:00.000Z", 21),
        _needs_row("/s/same.jsonl", "2026-06-20T05:00:00.000Z", 22),
    ]
    _patch_dashboard_io(monkeypatch, tmp_path, rows)

    async def run():
        app = TriageApp()
        app._self_window_id = 99
        monkeypatch.setattr(app, "_sync_right_pane", lambda: 21)
        async with app.run_test() as pilot:
            await pilot.pause()
            lv = app.query_one("#sessions", ListView)
            assert [c.row.window_id for c in lv.children] == [21, 22]
            assert "▶" in lv.children[0]._last_header
            assert "▶" not in lv.children[1]._last_header

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


def test_mark_toggle_via_keypress(monkeypatch, tmp_path):
    from triage import marks
    from triage.marks import MARK_GLYPH

    marks_path = tmp_path / "marks.json"
    monkeypatch.setattr(marks, "MARKS_PATH", marks_path)
    _patch_dashboard_io(monkeypatch, tmp_path, [_live_row()])

    async def run():
        app = TriageApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            lv = app.query_one("#sessions", ListView)
            assert MARK_GLYPH not in lv.children[0]._last_header
            await pilot.press("m")            # bookmark
            await pilot.pause()
            assert MARK_GLYPH in lv.children[0]._last_header
            assert marks.load_marks(marks_path) == {"/s/b.jsonl"}
            await pilot.press("m")            # un-bookmark (toggle off)
            await pilot.pause()
            assert MARK_GLYPH not in lv.children[0]._last_header
            assert marks.load_marks(marks_path) == set()

    asyncio.run(run())


def test_marked_filter_shows_only_bookmarks(monkeypatch, tmp_path):
    from triage import marks

    marks_path = tmp_path / "marks.json"
    monkeypatch.setattr(marks, "MARKS_PATH", marks_path)
    rows = [
        _needs_row("/s/a.jsonl", "2026-06-20T05:00:00.000Z", 1),
        _needs_row("/s/b.jsonl", "2026-06-20T04:00:00.000Z", 2),
    ]
    _patch_dashboard_io(monkeypatch, tmp_path, rows)

    def session_paths(lv):
        return [c.row.session_path for c in lv.children if isinstance(c, dashboard.SessionItem)]

    async def run():
        app = TriageApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            lv = app.query_one("#sessions", ListView)
            assert session_paths(lv) == ["/s/a.jsonl", "/s/b.jsonl"]
            # Bookmark only the second row.
            lv.index = 1
            await pilot.press("m")
            await pilot.pause()
            # Turn the filter on → only the bookmarked chat remains.
            await pilot.press("M")
            await pilot.pause()
            assert session_paths(lv) == ["/s/b.jsonl"]
            assert app._marks_only is True
            # Turn the filter off → both chats again.
            await pilot.press("M")
            await pilot.pause()
            assert session_paths(lv) == ["/s/a.jsonl", "/s/b.jsonl"]

    asyncio.run(run())


def test_preview_popup_opens_and_closes(monkeypatch, tmp_path):
    _patch_dashboard_io(monkeypatch, tmp_path, [_live_row()])
    monkeypatch.setattr(
        dashboard.summaries, "extract_recent_messages",
        lambda path, **kw: [("you", "do [the] thing"), ("codex", "on it")],
    )

    async def run():
        app = TriageApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("p")
            await pilot.pause()
            assert isinstance(app.screen, dashboard.PreviewScreen)
            # Message bodies are escaped so brackets can't be read as markup.
            rendered = [
                s.content for s in app.screen.query(dashboard.Static)
            ]
            assert any(r"do \[the] thing" in r for r in rendered)
            await pilot.press("escape")
            await pilot.pause()
            assert not isinstance(app.screen, dashboard.PreviewScreen)

    asyncio.run(run())


def test_preview_popup_opens_scrolled_to_bottom(monkeypatch, tmp_path):
    _patch_dashboard_io(monkeypatch, tmp_path, [_live_row()])
    # Enough turns to overflow the box so there's somewhere to scroll.
    pairs = [("you" if i % 2 == 0 else "codex", f"line {i}") for i in range(60)]
    monkeypatch.setattr(
        dashboard.summaries, "extract_recent_messages", lambda path, **kw: pairs
    )

    async def run():
        app = TriageApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("p")
            await pilot.pause()
            box = app.screen.query_one("#preview-box", dashboard.VerticalScroll)
            assert box.max_scroll_y > 0  # content overflows
            assert box.scroll_offset.y == box.max_scroll_y  # opened at the bottom

    asyncio.run(run())


def test_preview_popup_empty_messages(monkeypatch, tmp_path):
    _patch_dashboard_io(monkeypatch, tmp_path, [_live_row()])
    monkeypatch.setattr(
        dashboard.summaries, "extract_recent_messages", lambda path, **kw: []
    )

    async def run():
        app = TriageApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("p")
            await pilot.pause()
            assert isinstance(app.screen, dashboard.PreviewScreen)
            rendered = [s.content for s in app.screen.query(dashboard.Static)]
            assert any("no messages yet" in r for r in rendered)

    asyncio.run(run())


def test_is_dismissable_only_live_needs_you():
    assert TriageApp._is_dismissable(
        _needs_row("/s/a.jsonl", "2026-06-20T05:00:00.000Z", 1)
    ) is True
    assert TriageApp._is_dismissable(_live_row()) is False     # RUNNING (mid-task)
    assert TriageApp._is_dismissable(_hist_row("r")) is False  # already historical


def test_dismiss_closes_window_for_needs_you(monkeypatch, tmp_path):
    _patch_dashboard_io(
        monkeypatch, tmp_path,
        [_needs_row("/s/a.jsonl", "2026-06-20T05:00:00.000Z", 7)],
    )
    closed: list[int] = []
    monkeypatch.setattr(dashboard.kitty, "close_window", lambda w: closed.append(w))

    async def run():
        app = TriageApp()
        app._active_chat_win = 7  # this chat is the docked right pane
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("d")
            await pilot.pause()
            assert closed == [7]
            assert app._active_chat_win is None  # neighbor cache cleared

    asyncio.run(run())


def test_dismiss_ignores_running_chat(monkeypatch, tmp_path):
    _patch_dashboard_io(monkeypatch, tmp_path, [_live_row()])  # RUNNING
    closed: list[int] = []
    monkeypatch.setattr(dashboard.kitty, "close_window", lambda w: closed.append(w))

    async def run():
        app = TriageApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("d")
            await pilot.pause()
            assert closed == []  # a mid-task chat is never closed

    asyncio.run(run())


def test_regen_all_queues_every_visible_row(monkeypatch, tmp_path):
    rows = [
        _needs_row("/s/a.jsonl", "2026-06-20T05:00:00.000Z", 1),
        _needs_row("/s/b.jsonl", "2026-06-20T04:00:00.000Z", 2),
        _needs_row("/s/c.jsonl", "2026-06-20T03:00:00.000Z", 3),
    ]
    regen = _patch_dashboard_io(monkeypatch, tmp_path, rows)

    async def run():
        app = TriageApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("S")
            await pilot.pause()
            lv = app.query_one("#sessions", ListView)
            # Every visible row is now showing the pending placeholder.
            assert all(c._last_summary == "…" for c in lv.children)

    asyncio.run(run())
    assert regen.read_text() == "/s/a.jsonl\n/s/b.jsonl\n/s/c.jsonl\n"
