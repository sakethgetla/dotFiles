from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

MARKS_PATH = Path.home() / ".triage" / "marks.json"

# Marker glyph shown on a marked row's header. A bookmark fits the "come back to
# this later" intent better than a star/pin.
MARK_GLYPH = "🔖"


def load_marks(path: Path | None = None) -> set[str]:
    """Set of marked session paths. Missing/corrupt file → empty set."""
    path = path or MARKS_PATH
    if not path.exists():
        return set()
    try:
        with open(path) as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return set()
    paths = payload.get("marks")
    if not isinstance(paths, list):
        return set()
    return {p for p in paths if isinstance(p, str)}


def write_marks(marks: set[str], path: Path | None = None) -> None:
    path = path or MARKS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"marks": sorted(marks)}
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".marks-", suffix=".json")
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


def toggle_mark(session_path: str, path: Path | None = None) -> bool:
    """Add the mark if absent, remove it if present. Returns the new state."""
    path = path or MARKS_PATH
    marks = load_marks(path)
    if session_path in marks:
        marks.discard(session_path)
        marked = False
    else:
        marks.add(session_path)
        marked = True
    write_marks(marks, path)
    return marked
