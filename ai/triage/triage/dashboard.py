from __future__ import annotations

import asyncio
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
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Input, ListItem, ListView, Static

from . import agentsearch
from . import codex
from . import history
from . import hides
from . import kitty
from . import marks
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
    SessionItem { height: auto; padding: 0 1; border-bottom: solid $surface-lighten-2; }
    SessionItem .summary-full { color: $text-muted; height: 3; overflow-y: hidden; padding: 0 0 0 4; }
    SessionItem.-highlight .summary-full { height: auto; overflow-y: auto; padding: 0 0 1 4; }
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
        self._last_header = header
        self._last_summary = summary
        self._last_full_markup = self._full_markup(summary)
        self._header_static = Static(header, classes="header-line", markup=True)
        self._full = Static(self._last_full_markup, classes="summary-full", markup=True)

    @staticmethod
    def _summary(row: SessionRow, pending: bool) -> str:
        return row.summary or ("…" if pending else "(no summary yet)")

    def _full_markup(self, summary: str) -> str:
        return highlight(summary, self._query)

    def update_row(self, row: SessionRow, header: str, pending: bool, query: str = "") -> None:
        self.row = row
        self._query = query
        summary = self._summary(row, pending)
        if header != self._last_header:
            self._last_header = header
            self._header_static.update(header)
        full_markup = self._full_markup(summary)
        if summary != self._last_summary or full_markup != self._last_full_markup:
            self._last_summary = summary
            self._last_full_markup = full_markup
            self._full.update(full_markup)

    def compose(self) -> ComposeResult:
        yield self._header_static
        yield self._full


class PreviewScreen(ModalScreen):
    """A scrollable modal showing a chat's recent USER/AGENT conversation.

    Dismissed with esc/q/p. Its own escape binding consumes the key while it is
    the active screen, so the app-level escape handler (search/ask teardown) is
    never reached underneath it.
    """

    DEFAULT_CSS = """
    PreviewScreen { align: center middle; background: $background 60%; }
    PreviewScreen #preview-box {
        width: 80%; height: 80%;
        border: round $surface-lighten-2; background: $surface;
        padding: 0 1;
    }
    PreviewScreen .preview-role { text-style: bold; margin-top: 1; }
    PreviewScreen .preview-msg { margin-bottom: 1; }
    """

    BINDINGS = [
        Binding("escape,q,p", "dismiss_preview", "close"),
        Binding("j", "scroll_down", "down", show=False),
        Binding("k", "scroll_up", "up", show=False),
    ]

    def __init__(self, title: str, pairs: list[tuple[str, str]]) -> None:
        super().__init__()
        self._title = title or "(untitled)"
        self._pairs = pairs

    def compose(self) -> ComposeResult:
        box = VerticalScroll(id="preview-box")
        box.border_title = self._title
        with box:
            if not self._pairs:
                yield Static("[dim](no messages yet)[/]", markup=True)
                return
            for role, msg in self._pairs:
                color = "cyan" if role == "you" else "green"
                yield Static(f"[bold {color}]{role}[/]", classes="preview-role", markup=True)
                yield Static(escape(msg), classes="preview-msg", markup=True)

    def on_mount(self) -> None:
        # Open at the bottom: the newest turns are last, and that's what you
        # want to read first when peeking at a chat. Defer until after the first
        # refresh so the box is laid out and sized — scroll_end is a no-op while
        # content height is still zero.
        box = self.query_one("#preview-box", VerticalScroll)
        self.call_after_refresh(box.scroll_end, animate=False)

    def action_dismiss_preview(self) -> None:
        self.dismiss()

    def action_scroll_down(self) -> None:
        self.query_one("#preview-box", VerticalScroll).scroll_down()

    def action_scroll_up(self) -> None:
        self.query_one("#preview-box", VerticalScroll).scroll_up()


class TriageApp(App):
    CSS = """
    Screen { background: $background; }
    #counts { height: 1; padding: 0 1; color: $text-muted; }
    #search { display: none; height: 3; margin: 0 1; }
    #ask { display: none; height: 3; margin: 0 1; }
    ListView { height: 1fr; border: none; background: $background; }
    SessionItem .header-line { display: block; color: $text-muted; }
    SessionItem.-highlight .header-line { color: $text; text-style: bold; }
    """

    BINDINGS = [
        Binding("q", "quit", "quit"),
        Binding("r", "refresh", "refresh"),
        Binding("s", "regen_summary", "summary"),
        Binding("S", "regen_all", "regen all"),
        Binding("m", "toggle_mark", "mark"),
        Binding("M", "toggle_marked_filter", "bookmarks"),
        Binding("h", "toggle_hide", "hide"),
        Binding("H", "toggle_show_hidden", "show hidden"),
        Binding("d", "dismiss", "dismiss"),
        Binding("p", "preview", "preview"),
        Binding("n", "new_session", "new"),
        Binding("/", "search", "search"),
        Binding("a", "ask", "ask"),
        Binding("j", "cursor_down", "down", show=False),
        Binding("k", "cursor_up", "up", show=False),
        Binding("G", "cursor_bottom", "bottom", show=False),
    ]

    _self_window_id: int | None = None
    _self_tab_id: int | None = None
    _last_key: str | None = None

    def __init__(self) -> None:
        super().__init__()
        # Serializes refresh_data: the 0.5s interval and the direct calls from
        # key actions run on different tasks, so without this two refreshes can
        # interleave at an await inside the clear+mount below and mount the same
        # row ids twice (textual DuplicateIds crash).
        self._refresh_lock = asyncio.Lock()
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
        # Agent ("ask") search state. _ask_results is None when ask is inactive,
        # else the ranked list of matching session_paths (possibly empty). The
        # job runs on a dedicated single-worker pool; only one is in flight at a
        # time and a new submit supersedes any pending one.
        self._ask_query: str = ""
        self._ask_results: list[str] | None = None
        self._ask_pending: bool = False
        self._ask_future: Future[list[str]] | None = None
        self._ask_executor: ThreadPoolExecutor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="ask"
        )
        # Full candidate pool (live + history, unfiltered) snapshotted each
        # refresh; an `a` submit hands this to the agent so it can match against
        # every known chat, not just the rows currently displayed.
        self._ask_pool: list[SessionRow] = []
        # Marked session paths ("come back later" bookmarks), reloaded each
        # refresh so an external edit or a fresh toggle both take effect.
        self._marks: set[str] = set()
        # When True, the list is filtered to bookmarked chats only (toggled by M).
        self._marks_only: bool = False
        # Hidden session paths, reloaded each refresh. Hidden chats are dropped
        # from the list (and the search/ask pool) unless _show_hidden is on.
        self._hides: set[str] = set()
        # When True, hidden chats are revealed (with the 🚫 glyph) instead of
        # filtered out (toggled by H).
        self._show_hidden: bool = False
        # session_path → full transcript text (loaded in background)
        self._content_cache: dict[str, str] = {}
        self._content_executor: ThreadPoolExecutor = ThreadPoolExecutor(
            max_workers=4, thread_name_prefix="content"
        )
        self._content_futures: dict[str, Future[str | None]] = {}
        # The shell pane the dashboard spawns when it starts alone (see
        # _init_layout). Tracked so _replace_right_pane can close our own
        # placeholder while never touching a user's app pane.
        self._placeholder_win: int | None = None
        # Last known window id of the chat docked directly right of the
        # dashboard. kitty can only resolve "neighbor:right" relative to the
        # active window, so we refresh this whenever the dashboard holds focus
        # and reuse it otherwise (see _sync_right_pane).
        self._active_chat_win: int | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        search = Input(placeholder="search sessions and chats…", id="search")
        # Hidden by default; not in the focus chain until `/` reveals it, so the
        # list keeps keyboard focus and the bindings (s/n/j/k/…) fire normally.
        search.can_focus = False
        ask = Input(placeholder="ask: describe the chat you're looking for…", id="ask")
        ask.can_focus = False
        yield Vertical(
            Static("", id="counts"),
            search,
            ask,
            ListView(id="sessions"),
        )
        yield Footer()

    async def on_mount(self) -> None:
        self.title = "triage"
        self.sub_title = "j/k move  ↵ swap  p preview  n new  d dismiss  s summary  m mark  M bookmarks  h hide  H show-hidden  / search  a ask  r refresh  q quit"
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
            self._placeholder_win = kitty.launch_window_in_tab(self._self_tab_id)

    def _tab_for_window(self, window_id: int) -> int | None:
        for tab_id, _t, w, _wp, _fg in kitty.iter_tab_windows(kitty.ls()):
            if w == window_id:
                return tab_id
        return None

    def _sync_right_pane(self) -> int | None:
        """The pane docked directly to the right of the dashboard, or None.

        kitty only resolves `neighbor:right` relative to the *active* window, so
        we can ask for the dashboard's right-neighbor only while the dashboard
        holds focus — which is always true at action time (you pressed a key in
        it) and while you're looking at the list. When the dashboard isn't
        focused we keep the last value, so the chat doesn't appear to move just
        because you focused it. Spatial + overlay-safe (server-resolved), never
        the first sibling, so a third pane (dashboard | chat | app) is ignored.
        """
        if self._self_window_id is not None and kitty.window_is_focused(
            kitty.ls(), self._self_window_id
        ):
            self._active_chat_win = kitty.neighbor_right_of_active()
        return self._active_chat_win

    async def refresh_data(self) -> None:
        # Hold the lock for the whole rebuild so a concurrent refresh (interval
        # vs. action) can't interleave the clear+mount and double-mount rows.
        async with self._refresh_lock:
            await self._refresh_data()

    async def _refresh_data(self) -> None:
        # Drain content-cache background jobs
        for path in list(self._content_futures):
            fut = self._content_futures[path]
            if fut.done():
                try:
                    self._content_cache[path] = fut.result() or ""
                except Exception:
                    self._content_cache[path] = ""
                del self._content_futures[path]

        # Drain the agent ("ask") search job once it finishes.
        if self._ask_future is not None and self._ask_future.done():
            try:
                self._ask_results = self._ask_future.result()
            except Exception:
                self._ask_results = []
            self._ask_pending = False
            self._ask_future = None

        self._marks = marks.load_marks()
        self._hides = hides.load_hides()
        ds = state_module.read_state()
        sessions = ds.sessions if ds else []
        needs = [s for s in sessions if s.state == State.NEEDS_YOU]
        running = [s for s in sessions if s.state == State.RUNNING]
        # Surface the chat that started needing you most recently first: sort
        # NEEDS_YOU by last_event_at descending so the smallest idle age (least
        # time waiting) sits at the top. Stable sort keeps insertion order for
        # equal/missing timestamps. RUNNING stays below in its existing order.
        needs.sort(key=lambda s: s.last_event_at or "", reverse=True)
        ordered = needs + running

        # The chat docked directly to the right of the dashboard pins to the top
        # of the list and gets the ▶ marker. _sync_right_pane is the spatial
        # right-neighbor (not just any sibling), so a third pane doesn't steal
        # the indicator. Matched by window id, which is unique per row even when
        # forks transiently share a jsonl path.
        active_win = self._sync_right_pane()

        # Historical (previously-run) sessions: rescan ~/.codex/sessions every
        # HISTORY_SCAN_EVERY refreshes; re-filter against the current live paths
        # every refresh so a just-resumed session leaves the history block as
        # soon as the watcher promotes it (without waiting for the next scan).
        live_paths = {s.session_path for s in sessions}
        # Scan the full search pool only while a query is active; otherwise scan
        # just the display limit to keep per-tick disk reads bounded.
        query = self._search_query.strip()
        # Widen the history scan while a literal search OR an agent ("ask")
        # search is in play so both can reach sessions beyond the visible 40.
        ask_active = self._ask_pending or self._ask_results is not None
        scan_limit = HISTORY_SEARCH_LIMIT if (query or ask_active) else HISTORY_DISPLAY_LIMIT
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
        # Drop hidden chats from every block (and the ask pool below) unless
        # show-hidden mode is on. Done before the snapshot/search so search and
        # ask only reach hidden chats while they're revealed.
        if not self._show_hidden:
            ordered = [s for s in ordered if s.session_path not in self._hides]
            history_rows = [r for r in history_rows if r.session_path not in self._hides]
            display_history = [r for r in display_history if r.session_path not in self._hides]
        # Snapshot the full candidate pool (live + full history) for the agent
        # search before any filtering or display-limiting narrows it.
        self._ask_pool = list(ordered) + list(history_rows)

        # Search filtering: kick off background content loads then filter.
        # When searching, draw from the full HISTORY_SEARCH_LIMIT pool so
        # sessions beyond the visible 40 are reachable via search.
        if query:
            self._ensure_content_loaded(ordered + history_rows)
            ordered = [s for s in ordered if self._matches_search(s, query)]
            history_rows = [r for r in history_rows if self._matches_search(r, query)]
        elif ask_active:
            pass  # keep the full history pool; the ask filter below narrows it
        else:
            history_rows = display_history

        # Agent ("ask") search filter: narrow to the ranked matches and order
        # both blocks by the agent's relevance ranking. None ⇒ ask inactive.
        if self._ask_results is not None:
            rank = {p: i for i, p in enumerate(self._ask_results)}
            ordered = [s for s in ordered if s.session_path in rank]
            history_rows = [r for r in history_rows if r.session_path in rank]
            ordered.sort(key=lambda s: rank[s.session_path])
            history_rows.sort(key=lambda r: rank[r.session_path])

        # Bookmark-only filter (M): narrow both blocks to marked chats.
        if self._marks_only:
            ordered = [s for s in ordered if s.session_path in self._marks]
            history_rows = [r for r in history_rows if r.session_path in self._marks]

        # Pin the open (right-pane) chat to the top of whatever survived the
        # filters. Stable sort: False (0) for the active row, True (1) for the
        # rest, so the needs-you/running order below it is preserved.
        if active_win is not None:
            ordered.sort(key=lambda s: s.window_id != active_win)

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

        counts = self.query_one("#counts", Static)
        counts_text = f"[b red]NEEDS YOU {len(needs)}[/]   [b green]RUNNING {len(running)}[/]"
        if self._marks_only:
            counts_text += f"   [b]{marks.MARK_GLYPH} bookmarked only ({len(self._marks)})[/]"
        if self._show_hidden:
            counts_text += f"   [b]{hides.HIDE_GLYPH} showing hidden ({len(self._hides)})[/]"
        if self._ask_pending:
            counts_text += "   [b]🔎 searching…[/]"
        elif self._ask_results is not None:
            counts_text += f"   [b]🔎 ask: {escape(self._ask_query)} ({len(self._ask_results)})[/]"
        counts.update(counts_text)

        lv = self.query_one("#sessions", ListView)
        prev_index = lv.index
        prev_focused_path: str | None = None
        if prev_index is not None and 0 <= prev_index < len(lv.children):
            child = lv.children[prev_index]
            if isinstance(child, SessionItem):
                prev_focused_path = child.row.session_path

        def header_for(s: SessionRow) -> str:
            return self._format_header(
                s,
                s.session_path in self._marks,
                active_win is not None and s.window_id == active_win,
                s.session_path in self._hides,
            )

        entries: list[tuple[str, SessionRow | None, str, bool]] = []
        item_count = 0
        for s in ordered:
            pending = s.session_path in self._pending_regens
            entries.append(("session", s, header_for(s), pending))
            item_count += 1
        if history_rows:
            if query or self._ask_results is not None:
                entries.append(("history-divider", None, "── [bold]history[/bold] ──", False))
                for s in history_rows:
                    pending = s.session_path in self._pending_regens
                    entries.append(("session", s, header_for(s), pending))
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
                        entries.append(("session", s, header_for(s), pending))
                        item_count += 1
        if item_count == 0:
            if self._ask_results is not None:
                label = "  no chats matched your ask"
            elif self._marks_only:
                label = "  no bookmarked chats — press m on a chat to bookmark it"
            elif query:
                label = "  no results"
            else:
                label = "  no codex sessions detected"
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
    def _format_header(
        s: SessionRow, marked: bool = False, active: bool = False, hidden: bool = False
    ) -> str:
        # A bold title (the chat's headline) sits next to the status dot, with
        # idle time dimmed after it. Tab number/title are noise and omitted.
        # `active` ⇒ this chat is the one open in the right pane right now.
        # `hidden` ⇒ flagged hidden; only ever rendered in show-hidden mode,
        # since hidden rows are otherwise filtered out before this is called.
        mark = f"{marks.MARK_GLYPH} " if marked else ""
        hide_glyph = f"{hides.HIDE_GLYPH} " if hidden else ""
        active_glyph = "[bold cyan]▶[/] " if active else ""
        title = f"[bold]{escape(s.title)}[/] " if s.title else ""
        if s.kind == "historical":
            # No live pid/window; a hollow ○ distinguishes it from live ●. Glyph
            # leads, then the bold title, then the dim age — same order as live.
            return f"{active_glyph}{hide_glyph}{mark}[dim]○[/] {title}[dim]ran {humanize_age(s.last_event_at)} ago[/]"
        dot = "[red]●[/]" if s.state == State.NEEDS_YOU else "[green]●[/]"
        age = humanize_age(s.last_event_at)
        suffix = "" if s.state == State.NEEDS_YOU else " ago"
        verb = "idle" if s.state == State.NEEDS_YOU else "last ev"
        return f"{active_glyph}{hide_glyph}{mark}{dot} {title}[dim]{verb} {age}{suffix}[/]"

    def action_search(self) -> None:
        search = self.query_one("#search", Input)
        search.display = True
        search.can_focus = True
        search.focus()

    def action_ask(self) -> None:
        """Reveal the natural-language agent-search prompt and focus it."""
        ask = self.query_one("#ask", Input)
        ask.display = True
        ask.can_focus = True
        ask.focus()

    def _submit_ask(self, query: str) -> None:
        """Kick off a background agent search over the snapshotted pool."""
        self._ask_query = query
        self._ask_results = None
        self._ask_pending = True
        pool = list(self._ask_pool)
        self._ask_future = self._ask_executor.submit(
            agentsearch.semantic_search_blocking, query, pool
        )

    def _clear_ask(self) -> None:
        """Exit ask mode. Any in-flight job is orphaned (its result is dropped
        on the next drain because _ask_future is None)."""
        self._ask_query = ""
        self._ask_results = None
        self._ask_pending = False
        self._ask_future = None

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search":
            self._search_query = event.value

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "search":
            self.query_one("#sessions", ListView).focus()
        elif event.input.id == "ask":
            ask = self.query_one("#ask", Input)
            query = ask.value.strip()
            ask.display = False
            ask.can_focus = False
            self.query_one("#sessions", ListView).focus()
            if query:
                self._submit_ask(query)

    def on_key(self, event) -> None:
        if event.key == "g":
            if self._last_key == "g":
                self._last_key = None
                self.action_cursor_top()
            else:
                self._last_key = "g"
            return
        self._last_key = None
        if event.key == "escape":
            ask = self.query_one("#ask", Input)
            if ask.display:
                ask.display = False
                ask.can_focus = False
                self.query_one("#sessions", ListView).focus()
                return
            if self._ask_results is not None or self._ask_pending:
                self._clear_ask()
                return
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
        if row.title and q in row.title.lower():
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

    def action_cursor_top(self) -> None:
        """Move focus to the first selectable row (vim-style top jump)."""
        lv = self.query_one("#sessions", ListView)
        for i, child in enumerate(lv.children):
            if isinstance(child, SessionItem):
                lv.index = i
                break

    def action_cursor_bottom(self) -> None:
        """Move focus to the last selectable row (vim-style bottom jump)."""
        lv = self.query_one("#sessions", ListView)
        for i in range(len(lv.children) - 1, -1, -1):
            if isinstance(lv.children[i], SessionItem):
                lv.index = i
                break

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

    def action_preview(self) -> None:
        """Open a popup with the highlighted chat's recent conversation."""
        lv = self.query_one("#sessions", ListView)
        child = lv.highlighted_child
        if not isinstance(child, SessionItem):
            return
        pairs = summaries.extract_recent_messages(child.row.session_path)
        title = child.row.title or child.row.tab_title
        self.push_screen(PreviewScreen(title, pairs))

    async def action_toggle_mark(self) -> None:
        """Bookmark/unbookmark the highlighted chat to revisit it later."""
        lv = self.query_one("#sessions", ListView)
        child = lv.highlighted_child
        if not isinstance(child, SessionItem):
            return
        marks.toggle_mark(child.row.session_path)
        # repaint immediately so the glyph appears before the next refresh tick
        await self.refresh_data()

    async def action_toggle_marked_filter(self) -> None:
        """Toggle showing only bookmarked chats."""
        self._marks_only = not self._marks_only
        await self.refresh_data()

    async def action_toggle_hide(self) -> None:
        """Hide/unhide the highlighted chat from the default list view."""
        lv = self.query_one("#sessions", ListView)
        child = lv.highlighted_child
        if not isinstance(child, SessionItem):
            return
        hides.toggle_hide(child.row.session_path)
        # repaint immediately so the row drops/returns before the next refresh tick
        await self.refresh_data()

    async def action_toggle_show_hidden(self) -> None:
        """Toggle revealing hidden chats (with the 🚫 glyph) in the list."""
        self._show_hidden = not self._show_hidden
        await self.refresh_data()

    @staticmethod
    def _is_dismissable(row: SessionRow) -> bool:
        """A live chat idle awaiting you — safe to exit straight into history.

        Only NEEDS_YOU live rows qualify: codex there is parked waiting for
        input, so ending it loses no in-flight work. RUNNING chats (mid-task)
        and rows already in the history block are ineligible.
        """
        return row.kind == "live" and row.state == State.NEEDS_YOU

    async def action_dismiss(self) -> None:
        """Send the highlighted chat to history by exiting its codex session.

        Closing the chat's window ends codex exactly as typing `exit` inside it
        would; the rollout file stays on disk, so the history scanner re-surfaces
        it as an ordinary historical row on the watcher's next tick — there is no
        dismissed-state bookkeeping, and the result is indistinguishable from any
        other past session. Restricted to NEEDS_YOU live chats (_is_dismissable).
        """
        lv = self.query_one("#sessions", ListView)
        child = lv.highlighted_child
        if not isinstance(child, SessionItem) or not self._is_dismissable(child.row):
            return
        window_id = child.row.window_id
        kitty.close_window(window_id)
        if window_id == self._active_chat_win:
            self._active_chat_win = None
        # Nudge a history rescan so the chat reappears below as soon as the
        # watcher drops it from the live set (codex gone from the foreground).
        self._force_history_scan = True
        await self.refresh_data()

    async def action_regen_all(self) -> None:
        """Queue a regen for every chat currently listed (live + history)."""
        lv = self.query_one("#sessions", ListView)
        items = [c for c in lv.children if isinstance(c, SessionItem)]
        if not items:
            return
        REGEN_REQUESTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(REGEN_REQUESTS_PATH, "a") as f:
                f.write("".join(c.row.session_path + "\n" for c in items))
        except OSError:
            return
        deadline = time.monotonic() + PENDING_REGEN_TIMEOUT_SEC
        for c in items:
            path = c.row.session_path
            self._pending_regens[path] = c.row.summary
            self._pending_deadlines[path] = deadline
            c.row.summary = "…"
        # repaint immediately so all rows show "…" before the next refresh tick
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
            kitty.detach_window(right, "new")      # preserve the live session
        elif right == self._placeholder_win:
            kitty.close_window(right)              # discard our own placeholder shell
        # else: a pane the dashboard doesn't own (a user app) — leave it alone.

    def action_new_session(self) -> None:
        if self._self_tab_id is None:
            return
        right = self._sync_right_pane()
        right_is_codex = self._window_has_codex(right) if right is not None else False
        cwd = self._new_session_cwd()
        new_win = kitty.launch_command_in_tab(
            self._self_tab_id,
            [self._codex_command()],
            cwd=cwd,
            hold=True,
            copy_env=True,
            next_to=self._self_window_id,
            location="after",
        )
        if new_win is None:
            return
        self._replace_right_pane(new_win, right, right_is_codex)
        self._active_chat_win = new_win  # the new chat now occupies the right slot
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
        right = self._sync_right_pane()
        right_is_codex = self._window_has_codex(right) if right is not None else False
        cwd = row.cwd if row.cwd and os.path.isdir(row.cwd) else None
        new_win = kitty.launch_command_in_tab(
            self._self_tab_id,
            [self._plain_codex_command(), "resume", row.session_id],
            cwd=cwd,
            hold=True,
            copy_env=True,
            next_to=self._self_window_id,
            location="after",
        )
        if new_win is None:
            return  # launch failed; leave the existing right pane untouched
        self._replace_right_pane(new_win, right, right_is_codex)
        self._active_chat_win = new_win  # the resumed chat now occupies the right slot
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

        # Swap: send our current chat back to the clicked chat's tab, then pull
        # the clicked chat in. Only move the right pane if it's a real chat —
        # never relocate a user's app pane (or our placeholder) into another tab.
        right_pane = self._sync_right_pane()
        if right_pane is not None and self._window_has_codex(right_pane):
            kitty.detach_window(right_pane, target_tab)
        kitty.detach_window(window_id, self._self_tab_id)
        self._active_chat_win = window_id  # the swapped-in chat now occupies the right slot
        kitty.focus_window(window_id)


def main(argv: list[str] | None = None) -> int:
    TriageApp().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
