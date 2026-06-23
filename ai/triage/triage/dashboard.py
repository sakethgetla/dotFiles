from __future__ import annotations

import atexit
import os
import subprocess
import sys
import time
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

from rich.markup import escape
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Footer, Header, Input, ListItem, ListView, Static

from . import codex
from . import history
from . import kitty
from . import state as state_module
from . import summaries
from .state import SessionRow, State
from .summaries import REGEN_REQUESTS_PATH, extract_transcript


def humanize_age(iso_ts: str | None) -> str:
    if not iso_ts:
        return "?"
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    except ValueError:
        return "?"
    now = datetime.now(timezone.utc)
    delta = (now - dt).total_seconds()
    if delta < 0:
        delta = 0
    if delta < 60:
        return f"{int(delta)}s"
    if delta < 3600:
        return f"{int(delta / 60)}m"
    return f"{int(delta / 3600)}h"


SUMMARY_LINE_MAX = 100

# How long to keep showing "…" after an `s` press before giving up and
# reverting to the live summary. Must exceed the watcher's summary timeout
# (60s) plus a poll-cycle of margin, so a failed or no-op regen can't wedge
# the row on the placeholder indefinitely.
PENDING_REGEN_TIMEOUT_SEC = 90.0

# How many recent previously-run sessions to surface in the history block,
# and how often to re-scan ~/.codex/sessions for them. refresh_data runs at
# 0.5s; scanning every 10th refresh ≈ every 5s.
HISTORY_DISPLAY_LIMIT = 40   # rows shown in the default (no-search) view
HISTORY_SEARCH_LIMIT = 200   # rows scanned when a search query is active
HISTORY_SCAN_EVERY = 10


_BUCKET_LABELS: dict[str, str] = {
    "today": "today",
    "yesterday": "yesterday",
    "older": "history",
}


def _date_bucket(iso_ts: str | None) -> str:
    if not iso_ts:
        return "older"
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00")).astimezone()
        today = datetime.now().date()
        if dt.date() == today:
            return "today"
        if dt.date() == today - timedelta(days=1):
            return "yesterday"
    except ValueError:
        pass
    return "older"


def highlight(text: str, query: str) -> str:
    """Escape `text` for rich markup, wrapping case-insensitive `query` matches.

    Returns markup safe to embed in a larger markup string. With an empty query
    this is just escape(), so callers can pass it unconditionally.
    """
    if not query:
        return escape(text)
    low = text.lower()
    q = query.lower()
    parts: list[str] = []
    i = 0
    while True:
        j = low.find(q, i)
        if j == -1:
            parts.append(escape(text[i:]))
            break
        parts.append(escape(text[i:j]))
        parts.append(f"[black on yellow]{escape(text[j : j + len(q)])}[/]")
        i = j + len(q)
    return "".join(parts)


class SessionItem(ListItem):
    DEFAULT_CSS = """
    SessionItem { height: 1; padding: 0 1; }
    SessionItem.-highlight { height: auto; }
    SessionItem .summary-line { color: $text-muted; }
    SessionItem.-highlight .summary-line { display: none; }
    SessionItem .summary-full { display: none; color: $text-muted; padding: 0 0 1 4; }
    SessionItem.-highlight .summary-full { display: block; }
    """

    def __init__(
        self, row: SessionRow, header: str, pending: bool, index: int, query: str = ""
    ) -> None:
        # index (position among rendered SessionItems) keeps the DOM id unique;
        # historical rows share window_id=-1 so window_id can't be the id.
        super().__init__(id=f"row-{index}")
        self.row = row
        self._query = query
        summary = self._summary(row, pending)
        self._last_line_markup = self._line_markup(header, summary)
        self._last_header = header
        self._last_summary = summary
        self._last_full_markup = self._full_markup(summary)
        self._line = Static(self._last_line_markup, classes="summary-line", markup=True)
        self._full = Static(self._last_full_markup, classes="summary-full", markup=True)
        self._header_static = Static(header, classes="header-line", markup=True)

    @staticmethod
    def _summary(row: SessionRow, pending: bool) -> str:
        return row.summary or ("…" if pending else "(no summary yet)")

    def _line_markup(self, header: str, summary: str) -> str:
        line_text = highlight(summary.replace("\n", " ")[:SUMMARY_LINE_MAX], self._query)
        return f"{header}  [dim]{line_text}[/]"

    def _full_markup(self, summary: str) -> str:
        return highlight(summary, self._query)

    def update_row(self, row: SessionRow, header: str, pending: bool, query: str = "") -> None:
        self.row = row
        self._query = query
        summary = self._summary(row, pending)
        line_markup = self._line_markup(header, summary)
        if line_markup != self._last_line_markup:
            self._last_line_markup = line_markup
            self._line.update(line_markup)
        if header != self._last_header:
            self._last_header = header
            self._header_static.update(header)
        full_markup = self._full_markup(summary)
        if summary != self._last_summary or full_markup != self._last_full_markup:
            self._last_summary = summary
            self._last_full_markup = full_markup
            self._full.update(full_markup)

    def compose(self) -> ComposeResult:
        yield self._line
        yield self._header_static
        yield self._full


class TriageApp(App):
    CSS = """
    Screen { background: $background; }
    #counts { height: 1; padding: 0 1; color: $text-muted; }
    #search { display: none; height: 3; margin: 0 1; }
    ListView { height: 1fr; border: none; background: $background; }
    SessionItem .header-line { display: none; }
    SessionItem.-highlight .header-line { display: block; color: $text; text-style: bold; }
    """

    BINDINGS = [
        Binding("q", "quit", "quit"),
        Binding("r", "refresh", "refresh"),
        Binding("s", "regen_summary", "summary"),
        Binding("n", "new_session", "new"),
        Binding("/", "search", "search"),
        Binding("j", "cursor_down", "down", show=False),
        Binding("k", "cursor_up", "up", show=False),
    ]

    _self_window_id: int | None = None
    _self_tab_id: int | None = None

    def __init__(self) -> None:
        super().__init__()
        self._watcher_proc: subprocess.Popen | None = None
        # session_path → prior summary text at moment of `s` press.
        # Cleared when the live summary differs (i.e. watcher regenerated it)
        # or when the pending deadline below elapses, so a failed/unchanged
        # regen can never wedge the row on "…" forever.
        self._pending_regens: dict[str, str | None] = {}
        # session_path → monotonic deadline after which we stop forcing "…".
        self._pending_deadlines: dict[str, float] = {}
        # Cached historical rows (rescanned every HISTORY_SCAN_EVERY refreshes);
        # re-filtered against live paths on every refresh. Counter starts at 0
        # and _force_history_scan is True so the first refresh scans.
        self._history_raw: list[SessionRow] = []
        self._refresh_counter: int = 0
        self._force_history_scan: bool = True
        # Row count the current _history_raw was scanned at. Scanning is cheap
        # at the display limit but reads a prompt off disk per uncached session,
        # so we only widen to the search limit while a query is active.
        self._history_scan_limit: int = 0
        # Search state
        self._search_query: str = ""
        # session_path → full transcript text (loaded in background)
        self._content_cache: dict[str, str] = {}
        self._content_executor: ThreadPoolExecutor = ThreadPoolExecutor(
            max_workers=4, thread_name_prefix="content"
        )
        self._content_futures: dict[str, Future[str | None]] = {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        search = Input(placeholder="search sessions and chats…", id="search")
        # Hidden by default; not in the focus chain until `/` reveals it, so the
        # list keeps keyboard focus and the bindings (s/n/j/k/…) fire normally.
        search.can_focus = False
        yield Vertical(
            Static("", id="counts"),
            search,
            ListView(id="sessions"),
        )
        yield Footer()

    async def on_mount(self) -> None:
        self.title = "triage"
        self.sub_title = "j/k move  ↵ swap  n new  s summary  / search  r refresh  q quit"
        self._init_layout()
        self.set_interval(0.5, self.refresh_data)
        await self.refresh_data()
        self.query_one("#sessions", ListView).focus()
        self._watcher_proc = subprocess.Popen(
            [sys.executable, "-m", "triage.watcher"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        atexit.register(self._stop_watcher)

    def on_unmount(self) -> None:
        self._stop_watcher()

    def _stop_watcher(self) -> None:
        if self._watcher_proc and self._watcher_proc.poll() is None:
            self._watcher_proc.terminate()
            try:
                self._watcher_proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._watcher_proc.kill()
        self._watcher_proc = None

    def _init_layout(self) -> None:
        """Discover our own pane/tab; spawn a right-pane shell if we're alone."""
        ls_out = kitty.ls()
        my_pid = os.getpid()
        for tab_id, _t, window_id, window_pid, fg in kitty.iter_tab_windows(ls_out):
            if window_pid == my_pid or any(p.get("pid") == my_pid for p in fg):
                self._self_window_id = window_id
                self._self_tab_id = tab_id
                break
        if self._self_tab_id is None:
            return  # remote control unavailable; Enter falls back to focus

        kitty.set_tab_title(self._self_tab_id, "triage")

        siblings = [
            w for t, _t2, w, _wp, _fg in kitty.iter_tab_windows(ls_out)
            if t == self._self_tab_id and w != self._self_window_id
        ]
        if not siblings:
            kitty.launch_window_in_tab(self._self_tab_id)

    def _tab_for_window(self, window_id: int) -> int | None:
        for tab_id, _t, w, _wp, _fg in kitty.iter_tab_windows(kitty.ls()):
            if w == window_id:
                return tab_id
        return None

    def _current_right_pane(self) -> int | None:
        for tab_id, _t, w, _wp, _fg in kitty.iter_tab_windows(kitty.ls()):
            if tab_id == self._self_tab_id and w != self._self_window_id:
                return w
        return None

    async def refresh_data(self) -> None:
        # Drain content-cache background jobs
        for path in list(self._content_futures):
            fut = self._content_futures[path]
            if fut.done():
                try:
                    self._content_cache[path] = fut.result() or ""
                except Exception:
                    self._content_cache[path] = ""
                del self._content_futures[path]

        ds = state_module.read_state()
        sessions = ds.sessions if ds else []
        needs = [s for s in sessions if s.state == State.NEEDS_YOU]
        running = [s for s in sessions if s.state == State.RUNNING]
        ordered = needs + running

        # Historical (previously-run) sessions: rescan ~/.codex/sessions every
        # HISTORY_SCAN_EVERY refreshes; re-filter against the current live paths
        # every refresh so a just-resumed session leaves the history block as
        # soon as the watcher promotes it (without waiting for the next scan).
        live_paths = {s.session_path for s in sessions}
        # Scan the full search pool only while a query is active; otherwise scan
        # just the display limit to keep per-tick disk reads bounded.
        query = self._search_query.strip()
        scan_limit = HISTORY_SEARCH_LIMIT if query else HISTORY_DISPLAY_LIMIT
        # While a history regen is in flight, rescan every tick so the updated
        # cache entry is picked up as soon as the watcher writes it.
        if any(r.session_path in self._pending_regens for r in self._history_raw):
            self._force_history_scan = True
        # Entering search needs a wider scan than the last one covered.
        if scan_limit > self._history_scan_limit:
            self._force_history_scan = True
        if self._force_history_scan or self._refresh_counter % HISTORY_SCAN_EVERY == 0:
            self._history_raw = history.build_history_rows(
                scan_limit, live_paths, summaries.load_cache()
            )
            self._history_scan_limit = scan_limit
            self._force_history_scan = False
        self._refresh_counter += 1
        history_rows = [r for r in self._history_raw if r.session_path not in live_paths]
        display_history = history_rows[:HISTORY_DISPLAY_LIMIT]

        # Search filtering: kick off background content loads then filter.
        # When searching, draw from the full HISTORY_SEARCH_LIMIT pool so
        # sessions beyond the visible 40 are reachable via search.
        if query:
            self._ensure_content_loaded(ordered + history_rows)
            ordered = [s for s in ordered if self._matches_search(s, query)]
            history_rows = [r for r in history_rows if self._matches_search(r, query)]
        else:
            history_rows = display_history

        # Resolve pending: if live summary differs from the snapshot we took
        # at the moment of the `s` press, the watcher has regenerated. Otherwise,
        # force the row to render "…" to signal the request is in flight.
        for s in sessions:
            if s.session_path in self._pending_regens:
                prior = self._pending_regens[s.session_path]
                if s.summary and s.summary != prior:
                    self._clear_pending(s.session_path)
                elif time.monotonic() >= self._pending_deadlines.get(s.session_path, 0.0):
                    # regen failed, returned an unchanged value, or never
                    # arrived — stop forcing "…" and show the live summary.
                    self._clear_pending(s.session_path)
                else:
                    s.summary = "…"

        for s in history_rows:
            if s.session_path in self._pending_regens:
                prior = self._pending_regens[s.session_path]
                if s.summary and s.summary != prior:
                    self._clear_pending(s.session_path)
                elif time.monotonic() >= self._pending_deadlines.get(s.session_path, 0.0):
                    self._clear_pending(s.session_path)
                else:
                    s.summary = "…"

        tab_counts: dict[int, int] = {}
        for s in sessions:
            tab_counts[s.tab_id] = tab_counts.get(s.tab_id, 0) + 1

        counts = self.query_one("#counts", Static)
        counts.update(
            f"[b red]NEEDS YOU {len(needs)}[/]   [b green]RUNNING {len(running)}[/]"
        )

        lv = self.query_one("#sessions", ListView)
        prev_index = lv.index
        prev_focused_path: str | None = None
        if prev_index is not None and 0 <= prev_index < len(lv.children):
            child = lv.children[prev_index]
            if isinstance(child, SessionItem):
                prev_focused_path = child.row.session_path

        entries: list[tuple[str, SessionRow | None, str, bool]] = []
        item_count = 0
        for s in ordered:
            pending = s.session_path in self._pending_regens
            entries.append(("session", s, self._format_header(s, tab_counts, query), pending))
            item_count += 1
        if history_rows:
            if query:
                entries.append(("history-divider", None, "── [bold]history[/bold] ──", False))
                for s in history_rows:
                    pending = s.session_path in self._pending_regens
                    entries.append(("session", s, self._format_header(s, tab_counts, query), pending))
                    item_count += 1
            else:
                buckets: dict[str, list[SessionRow]] = {"today": [], "yesterday": [], "older": []}
                for r in history_rows:
                    buckets[_date_bucket(r.last_event_at)].append(r)
                for key in ("today", "yesterday", "older"):
                    rows_in = buckets[key]
                    if not rows_in:
                        continue
                    divider_id = f"history-divider-{key}"
                    entries.append((divider_id, None, f"── [bold]{_BUCKET_LABELS[key]}[/bold] ──", False))
                    for s in rows_in:
                        pending = s.session_path in self._pending_regens
                        entries.append(("session", s, self._format_header(s, tab_counts, query), pending))
                        item_count += 1
        if item_count == 0:
            label = "  no results" if query else "  no codex sessions detected"
            entries.append(("empty-state", None, label, False))

        if self._same_render_shape(lv, entries):
            for child, (kind, row, header, pending) in zip(lv.children, entries):
                if kind == "session" and isinstance(child, SessionItem) and row is not None:
                    child.update_row(row, header, pending, query)
            return

        # Build all items before touching the DOM, then swap atomically inside
        # batch_update so Textual suppresses intermediate renders — no empty-list
        # flash between clear and mount.
        new_items: list[ListItem] = []
        idx = 0
        for kind, row, header, pending in entries:
            if kind == "session" and row is not None:
                new_items.append(SessionItem(row, header, pending, idx, query))
                idx += 1
            elif kind.startswith("history-divider"):
                # Non-selectable divider; disabled=True keeps j/k from landing on it
                # and the isinstance guard in on_list_view_selected ignores Enter.
                new_items.append(ListItem(Static(header), id=kind, disabled=True))
            else:
                new_items.append(ListItem(Static(header), id=kind))

        with self.batch_update():
            await lv.clear()
            if new_items:
                await lv.mount(*new_items)

        # Restore highlight on the same session if still present, else by index.
        new_index: int | None = None
        if prev_focused_path is not None:
            for i, child in enumerate(lv.children):
                if isinstance(child, SessionItem) and child.row.session_path == prev_focused_path:
                    new_index = i
                    break
        if new_index is None and prev_index is not None and prev_index < len(lv.children):
            new_index = prev_index
        if new_index is None and lv.children:
            new_index = 0
        if new_index is not None:
            lv.index = new_index

    @staticmethod
    def _format_header(s: SessionRow, tab_counts: dict[int, int], query: str = "") -> str:
        if s.kind == "historical":
            # No live pid/window; a hollow ○ distinguishes it from live ●.
            title = highlight(s.tab_title or "(unknown)", query)
            return f"[dim]○[/] [{title}]  [dim]ran {humanize_age(s.last_event_at)} ago[/]"
        dot = "[red]●[/]" if s.state == State.NEEDS_YOU else "[green]●[/]"
        age = humanize_age(s.last_event_at)
        suffix = "" if s.state == State.NEEDS_YOU else " ago"
        verb = "idle" if s.state == State.NEEDS_YOU else "last ev"
        title = highlight(s.tab_title or "(untitled)", query)
        loc = (
            f"tab {s.tab_id}·w{s.window_id}"
            if tab_counts.get(s.tab_id, 0) > 1
            else f"tab {s.tab_id}"
        )
        return f"{dot} [{loc}] {title}  [dim]{verb} {age}{suffix}[/]"

    def action_search(self) -> None:
        search = self.query_one("#search", Input)
        search.display = True
        search.can_focus = True
        search.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search":
            self._search_query = event.value

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "search":
            self.query_one("#sessions", ListView).focus()

    def on_key(self, event) -> None:
        if event.key == "escape":
            search = self.query_one("#search", Input)
            if search.display:
                self._search_query = ""
                search.value = ""
                search.display = False
                search.can_focus = False
                self.query_one("#sessions", ListView).focus()

    def _matches_search(self, row: SessionRow, query: str) -> bool:
        q = query.lower()
        if row.tab_title and q in row.tab_title.lower():
            return True
        if row.summary and q in row.summary.lower():
            return True
        content = self._content_cache.get(row.session_path, "")
        return bool(content and q in content.lower())

    def _ensure_content_loaded(self, rows: list[SessionRow]) -> None:
        for row in rows:
            path = row.session_path
            if path not in self._content_cache and path not in self._content_futures:
                self._content_futures[path] = self._content_executor.submit(
                    extract_transcript, path
                )

    async def action_refresh(self) -> None:
        self._force_history_scan = True
        await self.refresh_data()

    def action_cursor_down(self) -> None:
        self.query_one("#sessions", ListView).action_cursor_down()

    def action_cursor_up(self) -> None:
        self.query_one("#sessions", ListView).action_cursor_up()

    def _same_render_shape(self, lv: ListView, entries: list[tuple[str, SessionRow | None, str, bool]]) -> bool:
        if len(lv.children) != len(entries):
            return False
        for child, (kind, row, _header, _pending) in zip(lv.children, entries):
            if kind == "session":
                if not isinstance(child, SessionItem) or row is None:
                    return False
                if child.row.kind != row.kind or child.row.session_path != row.session_path:
                    return False
            elif getattr(child, "id", None) != kind:
                return False
        return True

    async def action_regen_summary(self) -> None:
        lv = self.query_one("#sessions", ListView)
        child = lv.highlighted_child
        if not isinstance(child, SessionItem):
            return
        path = child.row.session_path
        REGEN_REQUESTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(REGEN_REQUESTS_PATH, "a") as f:
                f.write(path + "\n")
        except OSError:
            return
        self._pending_regens[path] = child.row.summary
        self._pending_deadlines[path] = time.monotonic() + PENDING_REGEN_TIMEOUT_SEC
        child.row.summary = "…"
        # repaint immediately so the user sees feedback before next refresh tick
        await self.refresh_data()

    def _clear_pending(self, path: str) -> None:
        self._pending_regens.pop(path, None)
        self._pending_deadlines.pop(path, None)

    @staticmethod
    def _codex_command() -> str:
        native = Path.home() / ".bun/bin/codex"
        return str(native) if native.exists() else "codex"

    @staticmethod
    def _plain_codex_command() -> str:
        """Plain OpenAI codex CLI (no account-rotation wrapper).

        Resume targets a session already bound to an account, so the wrapper's
        account picker is just friction here — use the bare CLI instead.
        """
        native = (
            Path.home()
            / ".bun/install/global/node_modules/@openai/codex/bin/codex.js"
        )
        return str(native) if native.exists() else "codex"

    @staticmethod
    def _new_session_cwd() -> str:
        return str(Path.home() / "yellowbox")

    def _window_has_codex(self, window_id: int) -> bool:
        """True if the given kitty window currently fronts a codex process.

        Returns False when the window isn't found (closed/detached since), so a
        vanished pane is never treated as a live session to preserve.
        """
        for _tab_id, _title, w, _wp, fg in kitty.iter_tab_windows(kitty.ls()):
            if w == window_id:
                return codex.find_codex_in_foreground(fg) is not None
        return False

    def _replace_right_pane(self, new_win: int, right: int | None, right_is_codex: bool) -> None:
        if right is None or right == new_win:
            return
        if right_is_codex:
            kitty.detach_window(right, "new")  # preserve the live session
        else:
            kitty.close_window(right)          # discard the placeholder shell

    def action_new_session(self) -> None:
        if self._self_tab_id is None:
            return
        right = self._current_right_pane()
        right_is_codex = self._window_has_codex(right) if right is not None else False
        cwd = self._new_session_cwd()
        new_win = kitty.launch_command_in_tab(
            self._self_tab_id,
            [self._codex_command()],
            cwd=cwd,
            hold=True,
            copy_env=True,
        )
        if new_win is None:
            return
        self._replace_right_pane(new_win, right, right_is_codex)
        kitty.focus_window(new_win)

    def _resume_historical(self, row: SessionRow) -> None:
        """Resume a previously-run session into the dashboard tab's right pane.

        Launches resume first (so the tab never drops below two panes), then
        clears the prior right pane: a live codex is detached to its own new tab
        (preserved, never closed); a placeholder shell is closed. --hold keeps
        the new pane visible if resume errors.
        """
        if self._self_tab_id is None or not row.session_id:
            return
        right = self._current_right_pane()
        right_is_codex = self._window_has_codex(right) if right is not None else False
        cwd = row.cwd if row.cwd and os.path.isdir(row.cwd) else None
        new_win = kitty.launch_command_in_tab(
            self._self_tab_id,
            [self._plain_codex_command(), "resume", row.session_id],
            cwd=cwd,
            hold=True,
            copy_env=True,
        )
        if new_win is None:
            return  # launch failed; leave the existing right pane untouched
        self._replace_right_pane(new_win, right, right_is_codex)
        kitty.focus_window(new_win)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item = event.item
        if not isinstance(item, SessionItem):
            return
        if item.row.kind == "historical":
            self._resume_historical(item.row)
            return
        window_id = item.row.window_id

        target_tab = self._tab_for_window(window_id)
        if (
            self._self_tab_id is None
            or target_tab is None
            or target_tab == self._self_tab_id
        ):
            kitty.focus_window(window_id)
            return

        right_pane = self._current_right_pane()
        if right_pane is not None:
            kitty.detach_window(right_pane, target_tab)
        kitty.detach_window(window_id, self._self_tab_id)
        kitty.focus_window(window_id)


def main(argv: list[str] | None = None) -> int:
    TriageApp().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
