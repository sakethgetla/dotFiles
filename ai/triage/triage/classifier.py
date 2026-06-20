from __future__ import annotations

import json
from pathlib import Path

from .state import State

# event_msg payload types that mark turn boundaries.
TERMINAL_TYPES = {"task_complete", "turn_aborted"}
ACTIVE_TYPES = {"task_started"}


def classify(
    jsonl_tail: list[dict], process_alive: bool
) -> tuple[State, str | None, str | None]:
    """Return (state, last_event_type, last_event_at).

    Walks the tail from newest to oldest. The first event_msg with a
    payload.type in TERMINAL_TYPES or ACTIVE_TYPES decides the state.

    Codex JSONL vocabulary (verified against real sessions):
      event_msg.payload.type ∈ {task_started, task_complete, turn_aborted,
        agent_message, user_message, token_count, patch_apply_end,
        context_compacted}
      response_item.payload.type ∈ {function_call, function_call_output,
        custom_tool_call, custom_tool_call_output, message, reasoning,
        tool_search_call, tool_search_output}

    Only task_started / task_complete / turn_aborted are lifecycle markers.
    Tool calls live on response_item and don't alter classification: between
    a task_started and a task_complete the session is RUNNING whether the
    last event is a tool call or a reasoning chunk.

    Mirrors arboretum (session_presence.rs:2358): wall-clock idle is never
    a flip signal while the process is alive. A dead process always means
    NEEDS_YOU regardless of last event.
    """
    if not jsonl_tail:
        if not process_alive:
            return (State.NEEDS_YOU, None, None)
        return (State.UNKNOWN, None, None)

    display_type: str | None = None
    display_at: str | None = None

    for ev in reversed(jsonl_tail):
        ts = ev.get("timestamp")
        ev_type = ev.get("type")
        payload = ev.get("payload") or {}
        ptype = payload.get("type")

        if display_type is None and ptype:
            display_type = ptype if ev_type == "event_msg" else f"{ev_type}:{ptype}"
            display_at = ts

        if ev_type == "event_msg":
            if ptype in TERMINAL_TYPES:
                return (State.NEEDS_YOU, ptype, ts)
            if ptype in ACTIVE_TYPES:
                if not process_alive:
                    return (State.NEEDS_YOU, ptype, ts)
                return (State.RUNNING, ptype, ts)

    if not process_alive:
        return (State.NEEDS_YOU, display_type, display_at)
    return (State.RUNNING, display_type, display_at)


TAIL_BYTES = 65536


def tail_jsonl(path: str | Path, max_lines: int = 50) -> list[dict]:
    """Return up to `max_lines` parsed JSON objects from the end of the file."""
    try:
        with open(path, "rb") as f:
            try:
                f.seek(0, 2)
                size = f.tell()
                f.seek(max(0, size - TAIL_BYTES))
            except OSError:
                f.seek(0)
            buf = f.read()
    except (FileNotFoundError, OSError):
        return []

    lines = buf.splitlines()[-max_lines:]
    out: list[dict] = []
    for raw in lines:
        if not raw.strip():
            continue
        try:
            out.append(json.loads(raw))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
    return out
