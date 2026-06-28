from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from triage import marks


def test_load_missing_returns_empty(tmp_path):
    assert marks.load_marks(tmp_path / "marks.json") == set()


def test_load_corrupt_returns_empty(tmp_path):
    p = tmp_path / "marks.json"
    p.write_text("{ not json")
    assert marks.load_marks(p) == set()


def test_toggle_adds_then_removes(tmp_path):
    p = tmp_path / "marks.json"
    assert marks.toggle_mark("/s/a.jsonl", p) is True
    assert marks.load_marks(p) == {"/s/a.jsonl"}
    assert marks.toggle_mark("/s/a.jsonl", p) is False
    assert marks.load_marks(p) == set()


def test_toggle_independent_paths(tmp_path):
    p = tmp_path / "marks.json"
    marks.toggle_mark("/s/a.jsonl", p)
    marks.toggle_mark("/s/b.jsonl", p)
    assert marks.load_marks(p) == {"/s/a.jsonl", "/s/b.jsonl"}
    marks.toggle_mark("/s/a.jsonl", p)
    assert marks.load_marks(p) == {"/s/b.jsonl"}
