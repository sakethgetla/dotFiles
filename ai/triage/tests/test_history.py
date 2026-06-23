from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from triage import history
from triage.history import (
    SessionMeta,
    build_history_rows,
    first_user_prompt,
    parse_session_meta,
    scan_recent,
    uuid_from_path,
)
from triage.state import State
from triage.summaries import SummaryEntry

UUID = "019ee367-ee3f-7ad1-98bb-de11875b9937"
ROLLOUT = f"rollout-2026-06-20T15-01-39-{UUID}.jsonl"


def _write_session(dir_path: Path, name: str, meta: dict | None, lines: list[dict] | None = None) -> Path:
    dir_path.mkdir(parents=True, exist_ok=True)
    p = dir_path / name
    rows: list[str] = []
    if meta is not None:
        rows.append(json.dumps({"type": "session_meta", "timestamp": "x", "payload": meta}))
    for line in lines or []:
        rows.append(json.dumps(line))
    p.write_text(("\n".join(rows) + "\n") if rows else "")
    return p


def _meta(**kw) -> dict:
    base = {"id": UUID, "cwd": "/Users/me/proj/myrepo", "timestamp": "2026-06-20T05:01:39.814Z",
            "git": {"commit_hash": "abc", "repository_url": "u", "branch": "main"}}
    base.update(kw)
    return base


# --- uuid_from_path ---

def test_uuid_from_path_valid():
    assert uuid_from_path(f"/a/b/{ROLLOUT}") == UUID


def test_uuid_from_path_malformed():
    assert uuid_from_path("/a/b/session.jsonl") is None


# --- parse_session_meta ---

def test_parse_session_meta_full(tmp_path):
    p = _write_session(tmp_path, ROLLOUT, _meta())
    m = parse_session_meta(str(p))
    assert m == SessionMeta(session_id=UUID, cwd="/Users/me/proj/myrepo",
                            branch="main", start_ts="2026-06-20T05:01:39.814Z")


def test_parse_session_meta_missing_git(tmp_path):
    p = _write_session(tmp_path, ROLLOUT, _meta(git=None))
    m = parse_session_meta(str(p))
    assert m is not None and m.branch is None and m.cwd == "/Users/me/proj/myrepo"


def test_parse_session_meta_git_without_branch(tmp_path):
    # real-world shape: git object present but no branch key.
    p = _write_session(tmp_path, ROLLOUT, _meta(git={"commit_hash": "abc", "repository_url": "u"}))
    m = parse_session_meta(str(p))
    assert m is not None and m.branch is None


def test_parse_session_meta_missing_cwd(tmp_path):
    meta = _meta()
    del meta["cwd"]
    p = _write_session(tmp_path, ROLLOUT, meta)
    m = parse_session_meta(str(p))
    assert m is not None and m.cwd is None


def test_parse_session_meta_corrupt_first_line_falls_back_to_filename(tmp_path):
    p = tmp_path / ROLLOUT
    p.write_text("{not json\n")
    m = parse_session_meta(str(p))
    assert m is not None and m.session_id == UUID and m.cwd is None


def test_parse_session_meta_id_missing_uses_filename(tmp_path):
    meta = _meta()
    del meta["id"]
    p = _write_session(tmp_path, ROLLOUT, meta)
    m = parse_session_meta(str(p))
    assert m is not None and m.session_id == UUID


def test_parse_session_meta_no_uuid_anywhere_returns_none(tmp_path):
    meta = _meta()
    del meta["id"]
    p = _write_session(tmp_path, "session.jsonl", meta)  # filename has no uuid
    assert parse_session_meta(str(p)) is None


# --- sub-agent detection / filtering ---

def _spawn_meta(parent="019d28a8-f193-7b20-a932-bf68508b8c35", depth=1, **kw) -> dict:
    return _meta(source={"subagent": {"thread_spawn": {"parent_thread_id": parent, "depth": depth}}}, **kw)


def test_parse_session_meta_subagent_flagged(tmp_path):
    p = _write_session(tmp_path, ROLLOUT, _spawn_meta())
    m = parse_session_meta(str(p))
    assert m is not None and m.is_subagent is True


def test_parse_session_meta_normal_not_subagent(tmp_path):
    p = _write_session(tmp_path, ROLLOUT, _meta())
    m = parse_session_meta(str(p))
    assert m is not None and m.is_subagent is False


def test_scan_recent_skips_subagents(tmp_path):
    d = tmp_path / "2026" / "06" / "20"
    u_sub = "019ee367-ee3f-7ad1-98bb-de11875b0003"
    _write_session(d, f"rollout-2026-06-20T08-00-00-{UUID}.jsonl", _meta(id=UUID, timestamp="a"))
    _write_session(d, f"rollout-2026-06-20T09-00-00-{u_sub}.jsonl", _spawn_meta(id=u_sub, timestamp="b"))
    got = scan_recent(limit=10, sessions_dir=tmp_path)
    ids = [m.session_id for _p, m in got]
    assert ids == [UUID] and u_sub not in ids


# --- first_user_prompt ---

def test_first_user_prompt_found(tmp_path):
    p = _write_session(tmp_path, ROLLOUT, _meta(), [
        {"type": "event_msg", "payload": {"type": "task_started"}},
        {"type": "event_msg", "payload": {"type": "user_message", "message": "first prompt"}},
        {"type": "event_msg", "payload": {"type": "user_message", "message": "second"}},
    ])
    assert first_user_prompt(str(p)) == "first prompt"


def test_first_user_prompt_byte_cap(tmp_path):
    # user_message sits past the byte cap → not found.
    big = {"type": "response_item", "payload": {"type": "reasoning", "content": "x" * 5000}}
    p = _write_session(tmp_path, ROLLOUT, _meta(), [
        big,
        {"type": "event_msg", "payload": {"type": "user_message", "message": "late"}},
    ])
    assert first_user_prompt(str(p), max_bytes=200) is None


def test_first_user_prompt_none(tmp_path):
    p = _write_session(tmp_path, ROLLOUT, _meta(), [
        {"type": "event_msg", "payload": {"type": "agent_message", "message": "hi"}},
    ])
    assert first_user_prompt(str(p)) is None


# --- scan_recent ---

def _sessions_tree(root: Path) -> Path:
    """Build a date-nested tree: two days, newest day has two files."""
    d1 = root / "2026" / "06" / "19"
    d2 = root / "2026" / "06" / "20"
    _write_session(d1, f"rollout-2026-06-19T09-00-00-{UUID}.jsonl", _meta(id=UUID, timestamp="d1"))
    u_a = "019ee367-ee3f-7ad1-98bb-de11875b0001"
    u_b = "019ee367-ee3f-7ad1-98bb-de11875b0002"
    _write_session(d2, f"rollout-2026-06-20T08-00-00-{u_a}.jsonl", _meta(id=u_a, timestamp="d2a"))
    _write_session(d2, f"rollout-2026-06-20T15-00-00-{u_b}.jsonl", _meta(id=u_b, timestamp="d2b"))
    return root


def test_scan_recent_newest_first(tmp_path):
    root = _sessions_tree(tmp_path)
    got = scan_recent(limit=10, sessions_dir=root)
    starts = [m.start_ts for _p, m in got]
    assert starts == ["d2b", "d2a", "d1"]  # newest day, newest file, first


def test_scan_recent_honours_cap_and_no_overread(tmp_path, monkeypatch):
    root = _sessions_tree(tmp_path)  # 3 sessions total
    calls = {"n": 0}
    real = history.parse_session_meta

    def counting(path):
        calls["n"] += 1
        return real(path)

    monkeypatch.setattr(history, "parse_session_meta", counting)
    got = scan_recent(limit=2, sessions_dir=root)
    assert len(got) == 2
    assert calls["n"] == 2  # stopped at the cap; did not parse the 3rd file


# --- build_history_rows ---

def test_build_history_rows_dedup_against_live(tmp_path):
    root = _sessions_tree(tmp_path)
    all_paths = [p for p, _m in scan_recent(10, sessions_dir=root)]
    live = {all_paths[0]}
    rows = build_history_rows(10, live, {}, sessions_dir=root)
    paths = {r.session_path for r in rows}
    assert all_paths[0] not in paths
    assert len(rows) == 2


def test_build_history_rows_label_cache_hit(tmp_path):
    p = _write_session(tmp_path / "2026" / "06" / "20", ROLLOUT, _meta())
    cache = {str(p): SummaryEntry("CACHED SUMMARY", "g", "s")}
    rows = build_history_rows(10, set(), cache, sessions_dir=tmp_path)
    assert rows[0].summary == "CACHED SUMMARY"


def test_build_history_rows_label_repo_branch_prompt(tmp_path):
    _write_session(tmp_path / "2026" / "06" / "20", ROLLOUT, _meta(), [
        {"type": "event_msg", "payload": {"type": "user_message", "message": "do the thing"}},
    ])
    rows = build_history_rows(10, set(), {}, sessions_dir=tmp_path)
    r = rows[0]
    assert r.summary == "myrepo·main — do the thing"
    assert r.tab_title == "myrepo·main"   # header bracket carries repo·branch
    assert r.kind == "historical"
    assert r.session_id == UUID
    assert r.cwd == "/Users/me/proj/myrepo"
    assert r.window_id == -1 and r.codex_pid == -1
    assert r.state == State.NEEDS_YOU


def test_build_history_rows_label_repo_branch_no_prompt(tmp_path):
    _write_session(tmp_path / "2026" / "06" / "20", ROLLOUT, _meta())  # no user_message
    rows = build_history_rows(10, set(), {}, sessions_dir=tmp_path)
    assert rows[0].summary == "myrepo·main"          # head alone, no " — prompt"
    assert rows[0].tab_title == "myrepo·main"


def test_build_history_rows_label_repo_no_branch_with_prompt(tmp_path):
    meta = _meta(git={"commit_hash": "abc", "repository_url": "u"})  # no branch
    _write_session(tmp_path / "2026" / "06" / "20", ROLLOUT, meta, [
        {"type": "event_msg", "payload": {"type": "user_message", "message": "ship it"}},
    ])
    rows = build_history_rows(10, set(), {}, sessions_dir=tmp_path)
    assert rows[0].summary == "myrepo — ship it"     # branch omitted from label
    assert rows[0].tab_title == "myrepo"             # and from the header bracket


def test_build_history_rows_label_basename_fallback(tmp_path):
    meta = _meta()
    del meta["cwd"]
    _write_session(tmp_path / "2026" / "06" / "20", ROLLOUT, meta)  # no cwd, no prompt
    rows = build_history_rows(10, set(), {}, sessions_dir=tmp_path)
    assert rows[0].summary == f"{ROLLOUT} — (no preview)"


def test_build_history_rows_last_event_at_uses_mtime(tmp_path):
    # last_event_at must reflect the file mtime (last activity), not the
    # session_meta start timestamp, so date bucketing groups by recency.
    p = _write_session(tmp_path / "2026" / "06" / "20", ROLLOUT, _meta())
    epoch = 1_700_000_000  # fixed integer seconds → exact millisecond ISO
    os.utime(p, (epoch, epoch))
    rows = build_history_rows(10, set(), {}, sessions_dir=tmp_path)
    expected = (
        datetime.fromtimestamp(epoch, timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )
    assert rows[0].last_event_at == expected
    assert rows[0].last_event_at != _meta()["timestamp"]  # not the start_ts
