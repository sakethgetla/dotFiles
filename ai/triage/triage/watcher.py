from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone

from . import codex, kitty
from . import state as state_module
from .classifier import classify, tail_jsonl
from .state import DashboardState, SessionRow, State

POLL_INTERVAL_SEC = 1.5
DASHBOARD_TAB_TITLE = "triage"

MARKER_GREEN = "🟢"
MARKER_YELLOW = "🟡"
MARKER_RED = "🔴"
MARKER_PREFIXES: tuple[str, ...] = (
    f"{MARKER_GREEN} ",
    f"{MARKER_YELLOW} ",
    f"{MARKER_RED} ",
)


def aggregate_marker(states: list[State]) -> str | None:
    """Map a tab's per-session states to a tab marker.

    UNKNOWN (codex alive, no JSONL yet) counts as needs-me.
    Rules:
      - all sessions running, none needs me   →  🟢
      - all sessions need me, none running    →  🔴
      - mix of running and needs me           →  🟡
    """
    if not states:
        return None
    needs_me = sum(
        1 for s in states if s in (State.NEEDS_YOU, State.UNKNOWN)
    )
    running = sum(1 for s in states if s == State.RUNNING)
    if needs_me == 0:
        return MARKER_GREEN
    if running == 0:
        return MARKER_RED
    return MARKER_YELLOW

log = logging.getLogger("triage.watcher")

# Maps tab_id → original (marker-stripped) title, so we can restore on shutdown.
_original_titles: dict[int, str] = {}


def _strip_marker(title: str) -> str:
    for prefix in MARKER_PREFIXES:
        if title.startswith(prefix):
            return title[len(prefix):]
    return title


def now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def tick(last_markers: dict[int, str]) -> dict[int, str]:
    sessions: list[SessionRow] = []
    tab_states: dict[int, list[State]] = {}
    tab_raw_titles: dict[int, str] = {}

    ls_out = kitty.ls()
    if not ls_out:
        log.debug("kitty @ ls returned nothing; skipping tick")
        return last_markers

    for tab_id, tab_title, window_id, _window_pid, fg_procs in kitty.iter_tab_windows(
        ls_out
    ):
        original_title = _strip_marker(tab_title)
        if original_title == DASHBOARD_TAB_TITLE:
            continue
        codex_pid = codex.find_codex_in_foreground(fg_procs)
        if codex_pid is None:
            continue
        session_path = codex.jsonl_for_pid(codex_pid)
        if not session_path:
            # codex is launched but hasn't created a JSONL yet
            # (no first prompt sent). Mark the tab green, no dashboard row.
            tab_states.setdefault(tab_id, []).append(State.UNKNOWN)
            tab_raw_titles[tab_id] = tab_title
            continue
        alive = codex.process_alive(codex_pid)
        tail = tail_jsonl(session_path)
        state, last_ev_type, last_ev_at = classify(tail, alive)
        sessions.append(
            SessionRow(
                tab_id=tab_id,
                window_id=window_id,
                tab_title=original_title,
                session_path=session_path,
                codex_pid=codex_pid,
                state=state,
                last_event_type=last_ev_type,
                last_event_at=last_ev_at,
            )
        )
        tab_states.setdefault(tab_id, []).append(state)
        tab_raw_titles[tab_id] = tab_title

    # Aggregate per-tab marker (one marker per tab, even with multiple sessions).
    new_markers: dict[int, str] = {}
    for tab_id, states_list in tab_states.items():
        marker = aggregate_marker(states_list)
        if marker is None:
            continue
        new_markers[tab_id] = marker
        raw_title = tab_raw_titles[tab_id]
        original = _strip_marker(raw_title)
        _original_titles[tab_id] = original
        desired = f"{marker} {original}"
        if desired != raw_title:
            kitty.set_tab_title(tab_id, desired)
            if last_markers.get(tab_id) != marker:
                log.info("tab %d → %s (n=%d)", tab_id, marker, len(states_list))

    # Restore titles for tabs that no longer have a codex session.
    for tab_id in last_markers:
        if tab_id not in new_markers:
            original = _original_titles.pop(tab_id, None)
            if original is not None:
                kitty.set_tab_title(tab_id, original)

    state_module.write_state(
        DashboardState(
            generated_at=now_iso(),
            watcher_pid=os.getpid(),
            sessions=sessions,
        )
    )

    return new_markers


def restore_all_titles() -> None:
    for tab_id, original in list(_original_titles.items()):
        try:
            kitty.set_tab_title(tab_id, original)
        except Exception:
            pass
    _original_titles.clear()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="triage watcher daemon")
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument(
        "--interval", type=float, default=POLL_INTERVAL_SEC, help="poll interval seconds"
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
    )
    log.info("triage watcher starting (pid=%d, interval=%.2fs)", os.getpid(), args.interval)

    last_markers: dict[int, str] = {}
    stop = False

    def handle_sig(signum, _frame):
        nonlocal stop
        log.info("received signal %d, stopping", signum)
        stop = True

    signal.signal(signal.SIGTERM, handle_sig)
    signal.signal(signal.SIGINT, handle_sig)

    try:
        while not stop:
            try:
                last_markers = tick(last_markers)
            except Exception:
                log.exception("tick failed")
            slept = 0.0
            while slept < args.interval and not stop:
                time.sleep(0.1)
                slept += 0.1
    finally:
        restore_all_titles()
        log.info("triage watcher stopped")

    return 0


if __name__ == "__main__":
    sys.exit(main())
