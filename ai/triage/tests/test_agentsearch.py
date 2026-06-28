from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from triage import agentsearch
from triage.agentsearch import (
    build_catalog,
    semantic_search_blocking,
    _parse_indices,
)
from triage.state import SessionRow, State


def _row(path: str, title: str = "", summary: str | None = None, tab_title: str = "") -> SessionRow:
    return SessionRow(
        tab_id=1,
        window_id=1,
        tab_title=tab_title,
        session_path=path,
        codex_pid=1,
        state=State.RUNNING,
        last_event_type=None,
        last_event_at=None,
        summary=summary,
        title=title,
    )


def test_build_catalog_numbers_rows_and_uses_title():
    rows = [
        _row("/a", title="Fix watcher tick", summary="Repairs the loop."),
        _row("/b", title="Add ask search", summary="Agent-backed search."),
    ]
    catalog = build_catalog(rows)
    lines = catalog.splitlines()
    assert lines[0] == "0\tFix watcher tick\tRepairs the loop."
    assert lines[1] == "1\tAdd ask search\tAgent-backed search."


def test_build_catalog_falls_back_to_tab_title_then_placeholder():
    rows = [
        _row("/a", title="", summary="body", tab_title="my_repo"),
        _row("/b", title="", summary=None, tab_title=""),
    ]
    lines = build_catalog(rows).splitlines()
    assert lines[0] == "0\tmy_repo\tbody"
    assert lines[1] == "1\t(untitled)\t(no summary)"


def test_build_catalog_truncates_summary_and_strips_tabs_newlines():
    rows = [_row("/a", title="t", summary="x\ty\nz" + "q" * 500)]
    line = build_catalog(rows, summary_max=10).splitlines()[0]
    idx, title, summary = line.split("\t")
    assert idx == "0"
    assert title == "t"
    assert len(summary) == 10
    assert "\t" not in summary and "\n" not in summary


def test_parse_indices_clean_array():
    assert _parse_indices("[2, 0, 1]", 3) == [2, 0, 1]


def test_parse_indices_filters_out_of_range_and_dupes():
    assert _parse_indices("[0, 5, 0, 2, -1]", 3) == [0, 2]


def test_parse_indices_tolerates_surrounding_prose_and_fences():
    assert _parse_indices("Here you go:\n```\n[1, 0]\n```", 3) == [1, 0]


def test_parse_indices_empty_array():
    assert _parse_indices("[]", 3) == []


def test_parse_indices_garbage_returns_empty():
    assert _parse_indices("no array here", 3) == []
    assert _parse_indices("[oops]", 3) == []


def test_parse_indices_excludes_booleans():
    # JSON true/false parse as bool (a subclass of int) — must not slip through.
    assert _parse_indices("[true, 1, false]", 3) == [1]


def test_semantic_search_maps_indices_to_paths(monkeypatch):
    rows = [_row("/a"), _row("/b"), _row("/c")]
    monkeypatch.setattr(agentsearch, "_run_codex_search", lambda q, c: "[2, 0]")
    assert semantic_search_blocking("find c then a", rows) == ["/c", "/a"]


def test_semantic_search_returns_empty_on_codex_failure(monkeypatch):
    rows = [_row("/a"), _row("/b")]
    monkeypatch.setattr(agentsearch, "_run_codex_search", lambda q, c: None)
    assert semantic_search_blocking("anything", rows) == []


def test_semantic_search_empty_query_or_rows_skips_codex(monkeypatch):
    called = False

    def boom(q, c):
        nonlocal called
        called = True
        return "[0]"

    monkeypatch.setattr(agentsearch, "_run_codex_search", boom)
    assert semantic_search_blocking("   ", [_row("/a")]) == []
    assert semantic_search_blocking("q", []) == []
    assert called is False
