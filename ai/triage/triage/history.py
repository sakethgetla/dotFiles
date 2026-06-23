from __future__ import annotations

import glob
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from . import codex
from .state import SessionRow, State
from .summaries import SummaryEntry

# rollout-<ts>-<uuid>.jsonl — capture the trailing 8-4-4-4-12 hex UUID.
_UUID_RE = re.compile(
    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", re.IGNORECASE
)
PROMPT_MAX_BYTES = 16384
LABEL_PROMPT_MAX = 80


@dataclass
class SessionMeta:
    session_id: str
    cwd: str | None
    branch: str | None
    start_ts: str | None
    is_subagent: bool = False


def uuid_from_path(path: str) -> str | None:
    """Extract the codex session UUID from a rollout-*.jsonl filename."""
    name = os.path.basename(path)
    m = _UUID_RE.search(name)
    return m.group(1) if m else None


def _is_subagent(payload: dict) -> bool:
    """True if this session was spawned as a sub-agent / sub-processor.

    Codex stamps the lineage at source.subagent.thread_spawn.parent_thread_id.
    """
    src = payload.get("source")
    sub = src.get("subagent") if isinstance(src, dict) else None
    spawn = sub.get("thread_spawn") if isinstance(sub, dict) else None
    return isinstance(spawn, dict) and bool(spawn.get("parent_thread_id"))


def parse_session_meta(path: str) -> SessionMeta | None:
    """Read the first JSONL line (session_meta) for resume metadata.

    Returns None only when no UUID can be recovered at all (neither from the
    record nor the filename) — such a session cannot be resumed. Tolerates a
    missing git object / branch and a missing cwd (both observed in real
    sessions). Swallows read/parse errors.
    """
    payload: dict = {}
    try:
        with open(path, "r", errors="replace") as f:
            first = f.readline()
        ev = json.loads(first)
        if ev.get("type") == "session_meta":
            payload = ev.get("payload") or {}
    except (OSError, json.JSONDecodeError, ValueError):
        payload = {}

    session_id = payload.get("id") or uuid_from_path(path)
    if not session_id:
        return None
    git = payload.get("git") or {}
    return SessionMeta(
        session_id=session_id,
        cwd=payload.get("cwd"),
        branch=git.get("branch") if isinstance(git, dict) else None,
        start_ts=payload.get("timestamp"),
        is_subagent=_is_subagent(payload),
    )


def first_user_prompt(path: str, max_bytes: int = PROMPT_MAX_BYTES) -> str | None:
    """Return the first user_message text, scanning at most max_bytes."""
    try:
        with open(path, "rb") as f:
            raw = f.read(max_bytes)
    except OSError:
        return None
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            ev = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if ev.get("type") != "event_msg":
            continue
        payload = ev.get("payload") or {}
        if payload.get("type") == "user_message":
            msg = payload.get("message")
            if isinstance(msg, str) and msg.strip():
                return msg
    return None


def scan_recent(limit: int = 40, sessions_dir=None) -> list[tuple[str, SessionMeta]]:
    """Return up to `limit` (path, meta) pairs, newest first.

    Enumerates only the date directories (YYYY/MM/DD) — bounded by days of use,
    not the full session-file count — and walks them newest-first (zero-padded
    paths sort lexically as chronologically). Within each day, files sort
    newest-first by their timestamped names. Stops as soon as `limit` valid
    metas are collected, so it never parses beyond the cap.
    """
    if sessions_dir is None:
        sessions_dir = codex.CODEX_SESSIONS_DIR
    out: list[tuple[str, SessionMeta]] = []
    day_dirs = sorted(glob.glob(os.path.join(str(sessions_dir), "*", "*", "*")), reverse=True)
    for day in day_dirs:
        files = sorted(glob.glob(os.path.join(day, "rollout-*.jsonl")), reverse=True)
        for path in files:
            meta = parse_session_meta(path)
            if meta is None or meta.is_subagent:
                continue
            out.append((path, meta))
            if len(out) >= limit:
                return out
    return out


def _display_title(meta: SessionMeta) -> str:
    """Header bracket title: '<repo>·<branch>', '<repo>', or '(unknown)'."""
    repo = os.path.basename(meta.cwd.rstrip("/")) if meta.cwd else None
    if repo and meta.branch:
        return f"{repo}·{meta.branch}"
    return repo or "(unknown)"


def _label(path: str, meta: SessionMeta, cache: dict[str, SummaryEntry]) -> str:
    """Build a one-line label without ever calling basename(None)."""
    entry = cache.get(path)
    if entry and entry.summary:
        return entry.summary
    repo = os.path.basename(meta.cwd.rstrip("/")) if meta.cwd else None
    prompt = first_user_prompt(path)
    prompt = prompt.replace("\n", " ").strip()[:LABEL_PROMPT_MAX] if prompt else None
    head = f"{repo}·{meta.branch}" if (repo and meta.branch) else repo
    if head and prompt:
        return f"{head} — {prompt}"
    if head:
        return head
    if prompt:
        return prompt
    return f"{os.path.basename(path)} — (no preview)"


def build_history_rows(
    limit: int,
    live_paths: set[str],
    cache: dict[str, SummaryEntry],
    sessions_dir=None,
) -> list[SessionRow]:
    """Scan recent sessions into historical SessionRows, dropping live ones.

    Rows are sentinel-valued (window_id/codex_pid/tab_id = -1) and in-memory
    only; they carry the resume UUID in session_id and the launch dir in cwd.
    """
    rows: list[SessionRow] = []
    for path, meta in scan_recent(limit, sessions_dir):
        if path in live_paths:
            continue
        label = _label(path, meta, cache)
        try:
            mtime_iso = (
                datetime.fromtimestamp(os.path.getmtime(path), timezone.utc)
                .isoformat(timespec="milliseconds")
                .replace("+00:00", "Z")
            )
        except OSError:
            mtime_iso = meta.start_ts
        rows.append(
            SessionRow(
                tab_id=-1,
                window_id=-1,
                tab_title=_display_title(meta),
                session_path=path,
                codex_pid=-1,
                state=State.NEEDS_YOU,
                last_event_type=None,
                last_event_at=mtime_iso,
                summary=label,
                kind="historical",
                session_id=meta.session_id,
                cwd=meta.cwd,
            )
        )
    return rows
