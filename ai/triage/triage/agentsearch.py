from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path

from .state import SessionRow
from .summaries import SUMMARY_MODEL

log = logging.getLogger("triage.agentsearch")

# Reuse the fast spark model the summariser already uses.
SEARCH_MODEL = SUMMARY_MODEL
SEARCH_TIMEOUT_SEC = 30
# Keep each catalog line short so a large session list still fits a small,
# fast prompt. Summaries are already ~500 chars; we clip harder here since the
# distinctive first sentence is what matters for matching.
CATALOG_SUMMARY_MAX = 240

SEARCH_PROMPT = (
    "You are a search assistant for a dashboard of coding-agent chat sessions. "
    "You are given a user's natural-language query describing the chat they are "
    "trying to find, and a numbered catalog of sessions. Each catalog line is "
    "`<index>\\t<title>\\t<summary>`.\n\n"
    "Return the indices of the sessions that match the query, most relevant "
    "first. Output format — follow exactly:\n"
    "- Output ONLY a JSON array of integers, e.g. `[3, 0, 7]`.\n"
    "- Use the exact index numbers from the catalog.\n"
    "- Order by relevance, most relevant first.\n"
    "- Include only genuinely relevant sessions; omit weak matches.\n"
    "- If nothing matches, output `[]`.\n"
    "- No prose, no explanation, no code fences — just the array.\n\n"
    "USER QUERY: "
)

_ARRAY = re.compile(r"\[[^\[\]]*\]")


def build_catalog(rows: list[SessionRow], summary_max: int = CATALOG_SUMMARY_MAX) -> str:
    """Number rows 0..n-1, one `idx\\ttitle\\tsummary` line each.

    Falls back to tab_title when the generated title is empty, and to a
    placeholder when there is no summary yet, so every row stays addressable by
    its index even when its metadata is sparse.
    """
    lines: list[str] = []
    for i, r in enumerate(rows):
        title = (r.title or r.tab_title or "(untitled)").replace("\t", " ").replace("\n", " ")
        summary = (r.summary or "(no summary)").replace("\t", " ").replace("\n", " ")
        if len(summary) > summary_max:
            summary = summary[:summary_max]
        lines.append(f"{i}\t{title}\t{summary}")
    return "\n".join(lines)


def _parse_indices(text: str, n: int) -> list[int]:
    """Extract the first JSON array of ints from `text`, kept in [0, n).

    Tolerant of stray prose or code fences around the array. Drops out-of-range
    values and duplicates while preserving order.
    """
    m = _ARRAY.search(text)
    if not m:
        return []
    try:
        raw = json.loads(m.group(0))
    except (json.JSONDecodeError, ValueError):
        return []
    if not isinstance(raw, list):
        return []
    out: list[int] = []
    seen: set[int] = set()
    for v in raw:
        if isinstance(v, bool):
            continue
        if not isinstance(v, int):
            continue
        if 0 <= v < n and v not in seen:
            seen.add(v)
            out.append(v)
    return out


def _run_codex_search(query: str, catalog: str) -> str | None:
    """One codex exec pass over the catalog. Returns raw output text, or None."""
    fd, out_path = tempfile.mkstemp(prefix="triage-search-", suffix=".txt")
    os.close(fd)
    try:
        try:
            subprocess.run(
                [
                    "codex", "exec",
                    "-m", SEARCH_MODEL,
                    "--ephemeral",
                    "--skip-git-repo-check",
                    "-s", "read-only",
                    "-o", out_path,
                    SEARCH_PROMPT + query,
                ],
                input=catalog,
                text=True,
                capture_output=True,
                timeout=SEARCH_TIMEOUT_SEC,
                check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            log.warning("ask search failed: %s", exc)
            return None
        try:
            text = Path(out_path).read_text().strip()
        except OSError:
            return None
        return text or None
    finally:
        try:
            Path(out_path).unlink()
        except OSError:
            pass


def semantic_search_blocking(query: str, rows: list[SessionRow]) -> list[str]:
    """Rank `rows` against `query` via codex spark; return ordered session_paths.

    Returns [] on empty input or any failure — the caller treats [] as "no
    matches" (distinct from None, which it uses for "not searched").
    """
    query = query.strip()
    if not query or not rows:
        return []
    catalog = build_catalog(rows)
    reply = _run_codex_search(query, catalog)
    if reply is None:
        return []
    indices = _parse_indices(reply, len(rows))
    return [rows[i].session_path for i in indices]
