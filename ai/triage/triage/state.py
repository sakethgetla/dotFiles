from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path


class State(str, Enum):
    NEEDS_YOU = "needs_you"
    RUNNING = "running"
    UNKNOWN = "unknown"


@dataclass
class SessionRow:
    tab_id: int
    window_id: int
    tab_title: str
    session_path: str
    codex_pid: int
    state: State
    last_event_type: str | None
    last_event_at: str | None
    summary: str | None = None
    # "live" (default) for watcher-discovered sessions; "historical" for rows
    # the dashboard builds by scanning ~/.codex/sessions. Historical rows are
    # in-memory only — they are never written through write_state().
    kind: str = "live"
    session_id: str | None = None  # codex UUID; resume target (historical only)
    cwd: str | None = None         # session_meta cwd; launch dir (historical only)


@dataclass
class DashboardState:
    generated_at: str
    watcher_pid: int
    sessions: list[SessionRow]


STATE_PATH = Path.home() / ".triage" / "state.json"


def write_state(state: DashboardState, path: Path = STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": state.generated_at,
        "watcher_pid": state.watcher_pid,
        "sessions": [
            {**asdict(s), "state": s.state.value} for s in state.sessions
        ],
    }
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".state-", suffix=".json")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def read_state(path: Path = STATE_PATH) -> DashboardState | None:
    if not path.exists():
        return None
    try:
        with open(path) as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    return DashboardState(
        generated_at=payload["generated_at"],
        watcher_pid=payload["watcher_pid"],
        sessions=[
            SessionRow(
                tab_id=s["tab_id"],
                window_id=s["window_id"],
                tab_title=s["tab_title"],
                session_path=s["session_path"],
                codex_pid=s["codex_pid"],
                state=State(s["state"]),
                last_event_type=s.get("last_event_type"),
                last_event_at=s.get("last_event_at"),
                summary=s.get("summary"),
                kind=s.get("kind", "live"),
                session_id=s.get("session_id"),
                cwd=s.get("cwd"),
            )
            for s in payload.get("sessions", [])
        ],
    )
