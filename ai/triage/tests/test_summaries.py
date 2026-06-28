from __future__ import annotations

import json
import os
import sys
import threading
import time
from concurrent.futures import Future
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from triage import summaries
from triage.summaries import (
    SummaryEntry,
    SummaryManager,
    drain_regen_requests,
    extract_recent_messages,
    extract_transcript,
    extract_user_messages,
    generate_summary_blocking,
    load_cache,
    prune_cache,
    write_cache,
    _looks_malformed,
    _render_action,
    _sanitize,
    _sanitize_title,
    _split_title_summary,
    _title_from_summary,
)


def _make_jsonl(tmp_path: Path, lines: list[dict]) -> Path:
    p = tmp_path / "session.jsonl"
    p.write_text("\n".join(json.dumps(l) for l in lines) + "\n")
    return p


def test_extract_transcript_messages_then_actions(tmp_path):
    p = _make_jsonl(tmp_path, [
        {"type": "event_msg", "payload": {"type": "task_started"}},
        {"type": "event_msg", "payload": {"type": "user_message", "message": "hello"}},
        {"type": "response_item", "payload": {"type": "reasoning", "content": "think"}},
        {"type": "response_item", "payload": {"type": "function_call", "name": "shell"}},
        {"type": "event_msg", "payload": {"type": "agent_message", "message": "world"}},
        {"type": "event_msg", "payload": {"type": "token_count", "info": {}}},
        {"type": "event_msg", "payload": {"type": "task_complete"}},
    ])
    text = extract_transcript(str(p))
    assert text == (
        "USER: hello\nAGENT: world\n\n"
        "--- RECENT ACTIVITY (oldest first) ---\nshell"
    )


def test_render_action_exec_and_spawn():
    assert _render_action(
        {"name": "exec_command", "arguments": json.dumps({"cmd": "git diff  lib.ts"})}
    ) == "exec: git diff lib.ts"
    assert _render_action(
        {"name": "spawn_agent", "arguments": json.dumps({"agent_type": "default", "message": "Read foo.md"})}
    ) == "spawn_agent(default): Read foo.md"
    # Unknown tool falls back to its bare name; nameless/empty → None.
    assert _render_action({"name": "wait_agent"}) == "wait_agent"
    assert _render_action({"name": "exec_command", "arguments": "{}"}) is None
    assert _render_action({}) is None


def test_extract_transcript_actions_block_grounds_status(tmp_path):
    p = _make_jsonl(tmp_path, [
        {"type": "event_msg", "payload": {"type": "user_message", "message": "fix the bug"}},
        {"type": "response_item", "payload": {
            "type": "function_call", "name": "exec_command",
            "arguments": json.dumps({"cmd": "rg watermark lib.ts"})}},
        {"type": "response_item", "payload": {
            "type": "function_call", "name": "spawn_agent",
            "arguments": json.dumps({"agent_type": "default", "message": "review this"})}},
    ])
    text = extract_transcript(str(p))
    assert "--- RECENT ACTIVITY (oldest first) ---" in text
    assert "exec: rg watermark lib.ts" in text
    assert "spawn_agent(default): review this" in text
    # Actions come after the message prose.
    assert text.index("USER: fix the bug") < text.index("exec: rg")


def test_extract_transcript_caps_action_count(tmp_path):
    lines = [{"type": "event_msg", "payload": {"type": "user_message", "message": "go"}}]
    for i in range(60):
        lines.append({"type": "response_item", "payload": {
            "type": "function_call", "name": "exec_command",
            "arguments": json.dumps({"cmd": f"echo {i}"})}})
    text = extract_transcript(str(_make_jsonl(tmp_path, lines)))
    exec_lines = [l for l in text.splitlines() if l.startswith("exec:")]
    assert len(exec_lines) == 40  # ACTIONS_MAX_COUNT, most recent kept
    assert "exec: echo 59" in text  # newest retained
    assert "exec: echo 0" not in text  # oldest dropped


def test_extract_transcript_tail_truncates(tmp_path):
    big_msg = "x" * 5000
    lines = [
        {"type": "event_msg", "payload": {"type": "user_message", "message": big_msg}}
        for _ in range(20)
    ]
    lines.append({"type": "event_msg", "payload": {"type": "user_message", "message": "FINAL"}})
    p = _make_jsonl(tmp_path, lines)
    text = extract_transcript(str(p), max_chars=10_000)
    assert len(text) <= 10_000
    assert text.endswith("USER: FINAL")


def test_extract_transcript_missing_file(tmp_path):
    assert extract_transcript(str(tmp_path / "nope.jsonl")) == ""


def test_extract_recent_messages_roles_and_order(tmp_path):
    p = _make_jsonl(tmp_path, [
        {"type": "event_msg", "payload": {"type": "task_started"}},
        {"type": "event_msg", "payload": {"type": "user_message", "message": "hi"}},
        {"type": "response_item", "payload": {"type": "function_call", "name": "shell"}},
        {"type": "event_msg", "payload": {"type": "agent_message", "message": "yo"}},
        {"type": "event_msg", "payload": {"type": "user_message", "message": "more"}},
    ])
    assert extract_recent_messages(str(p)) == [
        ("you", "hi"), ("codex", "yo"), ("you", "more"),
    ]


def test_extract_recent_messages_honors_max_messages(tmp_path):
    # Alternate roles so collapsing doesn't merge them, then cap to the last 3.
    lines = [
        {"type": "event_msg", "payload": {
            "type": "user_message" if i % 2 == 0 else "agent_message",
            "message": f"m{i}",
        }}
        for i in range(10)
    ]
    pairs = extract_recent_messages(str(_make_jsonl(tmp_path, lines)), max_messages=3)
    assert pairs == [("codex", "m7"), ("you", "m8"), ("codex", "m9")]


def test_extract_recent_messages_collapses_same_role_runs(tmp_path):
    p = _make_jsonl(tmp_path, [
        {"type": "event_msg", "payload": {"type": "user_message", "message": "u1"}},
        {"type": "event_msg", "payload": {"type": "agent_message", "message": "a1"}},
        {"type": "event_msg", "payload": {"type": "agent_message", "message": "a2"}},
        {"type": "event_msg", "payload": {"type": "agent_message", "message": "a3"}},
        {"type": "event_msg", "payload": {"type": "user_message", "message": "u2"}},
    ])
    # The codex run a1/a2/a3 collapses to its last (a3); result alternates.
    assert extract_recent_messages(str(p)) == [
        ("you", "u1"), ("codex", "a3"), ("you", "u2"),
    ]


def test_extract_recent_messages_tail_read_drops_partial_line(tmp_path):
    lines = [
        {"type": "event_msg", "payload": {"type": "user_message", "message": "first-old"}},
        {"type": "event_msg", "payload": {"type": "agent_message", "message": "kept"}},
    ]
    p = _make_jsonl(tmp_path, lines)
    # Budget chosen so the seek lands 10 bytes into line 1: the partial first
    # line is dropped, the whole second line survives, and it never raises.
    max_bytes = p.stat().st_size - 10
    pairs = extract_recent_messages(str(p), max_bytes=max_bytes)
    assert ("you", "first-old") not in pairs
    assert pairs == [("codex", "kept")]


def test_extract_recent_messages_missing_file(tmp_path):
    assert extract_recent_messages(str(tmp_path / "nope.jsonl")) == []


def test_extract_user_messages_only_user_turns(tmp_path):
    p = _make_jsonl(tmp_path, [
        {"type": "event_msg", "payload": {"type": "task_started"}},
        {"type": "event_msg", "payload": {"type": "user_message", "message": "first ask"}},
        {"type": "response_item", "payload": {"type": "reasoning", "content": "think"}},
        {"type": "response_item", "payload": {"type": "function_call", "name": "shell"}},
        {"type": "event_msg", "payload": {"type": "agent_message", "message": "agent reply"}},
        {"type": "event_msg", "payload": {"type": "user_message", "message": "second ask"}},
        {"type": "event_msg", "payload": {"type": "task_complete"}},
    ])
    text = extract_user_messages(str(p))
    # Only the two user messages, in order; no agent/reasoning/action content.
    assert text == "first ask\nsecond ask"
    assert "agent reply" not in text
    assert "shell" not in text
    assert "RECENT ACTIVITY" not in text


def test_extract_user_messages_survives_compaction(tmp_path):
    # JSONL is append-only: user_message events before a context_compacted
    # marker remain in the file and must still be extracted.
    p = _make_jsonl(tmp_path, [
        {"type": "event_msg", "payload": {"type": "user_message", "message": "before"}},
        {"type": "event_msg", "payload": {"type": "context_compacted"}},
        {"type": "event_msg", "payload": {"type": "user_message", "message": "after"}},
    ])
    assert extract_user_messages(str(p)) == "before\nafter"


def test_extract_user_messages_tail_truncates(tmp_path):
    big = "x" * 5000
    lines = [
        {"type": "event_msg", "payload": {"type": "user_message", "message": big}}
        for _ in range(20)
    ]
    lines.append({"type": "event_msg", "payload": {"type": "user_message", "message": "FINAL"}})
    text = extract_user_messages(str(_make_jsonl(tmp_path, lines)), max_chars=10_000)
    assert len(text) <= 10_000
    assert text.endswith("FINAL")


def test_extract_user_messages_missing_file(tmp_path):
    assert extract_user_messages(str(tmp_path / "nope.jsonl")) == ""


def test_load_cache_missing_returns_empty(tmp_path):
    assert load_cache(tmp_path / "missing.json") == {}


def test_load_cache_corrupt_returns_empty(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json")
    assert load_cache(p) == {}


def test_write_then_load_roundtrip(tmp_path):
    p = tmp_path / "summaries.json"
    cache = {
        "/x/y.jsonl": SummaryEntry(
            summary="topic — status",
            generated_at="2026-06-21T10:00:00Z",
            source_last_event_at="2026-06-21T09:59:58Z",
        )
    }
    write_cache(cache, p)
    loaded = load_cache(p)
    assert loaded == cache


def test_write_cache_no_tmp_lingers(tmp_path):
    p = tmp_path / "summaries.json"
    write_cache({"/a.jsonl": SummaryEntry("s", "t", "u")}, p)
    leftovers = [f for f in tmp_path.iterdir() if f.name.startswith(".summaries-")]
    assert leftovers == []


def _entry() -> SummaryEntry:
    return SummaryEntry("topic — status", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z")


def test_prune_cache_drops_missing_jsonl(tmp_path):
    present = _make_jsonl(tmp_path, [{"type": "event_msg", "payload": {"type": "task_complete"}}])
    cache = {str(present): _entry(), str(tmp_path / "gone.jsonl"): _entry()}
    removed = prune_cache(cache)
    assert removed == 1
    assert str(present) in cache
    assert str(tmp_path / "gone.jsonl") not in cache


def test_prune_cache_drops_old_by_mtime(tmp_path):
    fresh = _make_jsonl(tmp_path, [{"type": "x"}])
    old = tmp_path / "old.jsonl"
    old.write_text("{}\n")
    now = 1_000_000_000.0
    os.utime(fresh, (now, now))
    os.utime(old, (now - 31 * 86400, now - 31 * 86400))
    cache = {str(fresh): _entry(), str(old): _entry()}
    removed = prune_cache(cache, max_age_days=30, now=now)
    assert removed == 1
    assert str(fresh) in cache
    assert str(old) not in cache


def test_prune_cache_keeps_active_session_with_old_summary(tmp_path):
    # JSONL touched recently even though the cached summary timestamp is ancient.
    active = _make_jsonl(tmp_path, [{"type": "x"}])
    now = 1_000_000_000.0
    os.utime(active, (now - 60, now - 60))
    cache = {str(active): _entry()}
    assert prune_cache(cache, max_age_days=30, now=now) == 0
    assert str(active) in cache


def test_looks_malformed_detects_list_shapes():
    assert _looks_malformed("1. Reconfirm scope and evidence")
    assert _looks_malformed("2) do the thing")
    assert _looks_malformed("- bullet point")
    assert _looks_malformed("* star bullet")
    # URLs are no longer flagged malformed — sanitize tidies them instead.
    assert not _looks_malformed("topic — see https://example.com/x for detail")
    assert not _looks_malformed("SCIM P1 garbled-upn issue — confirmed and fixed")


def test_sanitize_strips_numbering_and_url_without_truncating():
    tail = "x" * 600
    bad = "1. Reconfirm scope — refs https://slack.com/archives/abc " + tail
    out = _sanitize(bad)
    assert not out.startswith("1.")
    assert "http" not in out
    # No length cap: the full body is preserved and never ends with an ellipsis.
    assert tail in out
    assert not out.endswith("…")


def test_sanitize_passes_clean_line_through():
    good = "triage dashboard work — fixed flicker; done"
    assert _sanitize(good) == good


def test_split_title_summary_with_marker():
    title, body = _split_title_summary("TITLE: Fix SCIM mapping\n\nThe body goes here.")
    assert title == "Fix SCIM mapping"
    assert body == "The body goes here."


def test_split_title_summary_case_insensitive_and_inline():
    # Marker need not be the very first line; match is case-insensitive and the
    # marker line is removed from the body.
    title, body = _split_title_summary("\ntitle: lower marker\nrest of summary")
    assert title == "lower marker"
    assert body == "rest of summary"


def test_split_title_summary_no_marker():
    title, body = _split_title_summary("Just a plain summary with no marker.")
    assert title == ""
    assert body == "Just a plain summary with no marker."


def test_sanitize_title_strips_and_caps():
    assert _sanitize_title('  "Quoted Title."  ') == "Quoted Title"
    assert _sanitize_title("TITLE: leftover prefix") == "leftover prefix"
    long = "word " * 30
    out = _sanitize_title(long)
    assert len(out) <= summaries.TITLE_MAX_CHARS
    assert out.endswith("…")


def test_title_from_summary_takes_first_words():
    assert _title_from_summary("Fixing the watcher tick loop and more text here") == (
        "Fixing the watcher tick loop and"
    )


def test_load_cache_drops_on_version_mismatch(tmp_path):
    p = tmp_path / "summaries.json"
    p.write_text(json.dumps({
        "version": 1,
        "entries": {"/a.jsonl": {
            "summary": "old", "generated_at": "t", "source_last_event_at": "u"
        }},
    }))
    # v1 file predates titles → dropped wholesale so the watcher regenerates.
    assert load_cache(p) == {}


def test_write_then_load_roundtrip_preserves_title(tmp_path):
    p = tmp_path / "summaries.json"
    cache = {"/x.jsonl": SummaryEntry(
        summary="body", generated_at="g", source_last_event_at="s", title="Headline"
    )}
    write_cache(cache, p)
    assert load_cache(p) == cache


def test_generate_summary_retries_once_on_malformed(monkeypatch, tmp_path):
    p = _make_jsonl(tmp_path, [
        {"type": "event_msg", "payload": {"type": "user_message", "message": "hi"}},
    ])
    calls: list[str] = []

    def fake_run(session_path, transcript, prompt):
        calls.append(prompt)
        # First pass: body is list-shaped. Retry: clean title + body.
        if len(calls) == 1:
            return "TITLE: plan\n\n1. a plan item"
        return "TITLE: the topic\n\ntopic — done"

    monkeypatch.setattr(summaries, "_run_codex_summary", fake_run)
    out = generate_summary_blocking(str(p))
    assert out == ("the topic", "topic — done")
    assert len(calls) == 2
    assert calls[0] == summaries.SUMMARY_PROMPT
    assert calls[1] == summaries.SUMMARY_RETRY_PROMPT


def test_generate_summary_no_retry_when_clean(monkeypatch, tmp_path):
    p = _make_jsonl(tmp_path, [
        {"type": "event_msg", "payload": {"type": "user_message", "message": "hi"}},
    ])
    calls: list[str] = []

    def fake_run(session_path, transcript, prompt):
        calls.append(prompt)
        return "TITLE: already good\n\ntopic — already good"

    monkeypatch.setattr(summaries, "_run_codex_summary", fake_run)
    assert generate_summary_blocking(str(p)) == ("already good", "topic — already good")
    assert len(calls) == 1


def test_generate_summary_derives_title_when_marker_missing(monkeypatch, tmp_path):
    # Model ignored the TITLE format → title falls back to the summary's opening.
    p = _make_jsonl(tmp_path, [
        {"type": "event_msg", "payload": {"type": "user_message", "message": "hi"}},
    ])

    def fake_run(session_path, transcript, prompt):
        return "Refactoring the watcher tick loop for clarity and speed."

    monkeypatch.setattr(summaries, "_run_codex_summary", fake_run)
    title, summary = generate_summary_blocking(str(p))
    assert summary.startswith("Refactoring the watcher")
    assert title == "Refactoring the watcher tick loop for"  # first 6 words


def test_generate_summary_sanitizes_when_retry_still_malformed(monkeypatch, tmp_path):
    p = _make_jsonl(tmp_path, [
        {"type": "event_msg", "payload": {"type": "user_message", "message": "hi"}},
    ])

    def fake_run(session_path, transcript, prompt):
        return "TITLE: list thing\n\n1. still a list — https://x.com/y"

    monkeypatch.setattr(summaries, "_run_codex_summary", fake_run)
    title, summary = generate_summary_blocking(str(p))
    assert not summary.startswith("1.")
    assert "http" not in summary
    assert title == "list thing"


def test_drain_regen_requests_consumes_and_deletes(tmp_path):
    p = tmp_path / "regen.requests"
    p.write_text("/a.jsonl\n/b.jsonl\n\n/a.jsonl\n")
    got = drain_regen_requests(p)
    assert got == {"/a.jsonl", "/b.jsonl"}
    assert not p.exists()


def test_drain_regen_requests_empty_when_absent(tmp_path):
    assert drain_regen_requests(tmp_path / "nope") == set()


def test_summary_manager_dedupes_in_flight(monkeypatch):
    gate = threading.Event()

    def slow(path: str) -> str | None:
        gate.wait(timeout=2)
        return "x"

    monkeypatch.setattr(summaries, "generate_summary_blocking", slow)
    mgr = SummaryManager(max_workers=2)
    try:
        assert mgr.submit("/p.jsonl", "t1") is True
        assert mgr.submit("/p.jsonl", "t1") is False
        gate.set()
        # wait for completion
        for _ in range(50):
            done = mgr.drain_completed()
            if done:
                break
            time.sleep(0.05)
        else:
            done = []
        assert any(p == "/p.jsonl" and s == "x" for p, _, s in done)
        # now a fresh submit succeeds
        gate.clear()
        gate.set()
        assert mgr.submit("/p.jsonl", "t2") is True
    finally:
        mgr.shutdown()


def test_summary_manager_drain_returns_tuples(monkeypatch):
    monkeypatch.setattr(summaries, "generate_summary_blocking", lambda p: "ok")
    mgr = SummaryManager(max_workers=1)
    try:
        mgr.submit("/p.jsonl", "src")
        for _ in range(50):
            done = mgr.drain_completed()
            if done:
                break
            time.sleep(0.05)
        else:
            done = []
        assert done == [("/p.jsonl", "src", "ok")]
    finally:
        mgr.shutdown()


def test_summary_manager_handles_job_exception(monkeypatch):
    def boom(path):
        raise RuntimeError("nope")

    monkeypatch.setattr(summaries, "generate_summary_blocking", boom)
    mgr = SummaryManager(max_workers=1)
    try:
        mgr.submit("/p.jsonl", "src")
        for _ in range(50):
            done = mgr.drain_completed()
            if done:
                break
            time.sleep(0.05)
        else:
            done = []
        assert done == [("/p.jsonl", "src", None)]
    finally:
        mgr.shutdown()
