from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

HIDES_PATH = Path.home() / ".triage" / "hides.json"

# Marker glyph shown on a hidden row's header while "show hidden" mode is on.
# A prohibited sign reads as "suppressed from the normal view".
HIDE_GLYPH = "🚫"


def load_hides(path: Path | None = None) -> set[str]:
    """Set of hidden session paths. Missing/corrupt file → empty set."""
    path = path or HIDES_PATH
    if not path.exists():
        return set()
    try:
        with open(path) as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return set()
    paths = payload.get("hides")
    if not isinstance(paths, list):
        return set()
    return {p for p in paths if isinstance(p, str)}


def write_hides(hides: set[str], path: Path | None = None) -> None:
    path = path or HIDES_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"hides": sorted(hides)}
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".hides-", suffix=".json")
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


def toggle_hide(session_path: str, path: Path | None = None) -> bool:
    """Add the hide if absent, remove it if present. Returns the new state."""
    path = path or HIDES_PATH
    hides = load_hides(path)
    if session_path in hides:
        hides.discard(session_path)
        hidden = False
    else:
        hides.add(session_path)
        hidden = True
    write_hides(hides, path)
    return hidden
