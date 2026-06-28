from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from triage import hides


def test_load_missing_returns_empty(tmp_path):
    assert hides.load_hides(tmp_path / "hides.json") == set()


def test_load_corrupt_returns_empty(tmp_path):
    p = tmp_path / "hides.json"
    p.write_text("{ not json")
    assert hides.load_hides(p) == set()


def test_toggle_adds_then_removes(tmp_path):
    p = tmp_path / "hides.json"
    assert hides.toggle_hide("/s/a.jsonl", p) is True
    assert hides.load_hides(p) == {"/s/a.jsonl"}
    assert hides.toggle_hide("/s/a.jsonl", p) is False
    assert hides.load_hides(p) == set()


def test_toggle_independent_paths(tmp_path):
    p = tmp_path / "hides.json"
    hides.toggle_hide("/s/a.jsonl", p)
    hides.toggle_hide("/s/b.jsonl", p)
    assert hides.load_hides(p) == {"/s/a.jsonl", "/s/b.jsonl"}
    hides.toggle_hide("/s/a.jsonl", p)
    assert hides.load_hides(p) == {"/s/b.jsonl"}
