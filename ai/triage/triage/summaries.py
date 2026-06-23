from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import tempfile
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path

log = logging.getLogger("triage.summaries")

SUMMARIES_PATH = Path.home() / ".triage" / "summaries.json"
REGEN_REQUESTS_PATH = Path.home() / ".triage" / "regen.requests"
SUMMARY_MODEL = "gpt-5.3-codex-spark"
SUMMARY_TIMEOUT_SEC = 60
SUMMARY_PROMPT = (
    "You are writing a quick recap of a coding session for a dashboard, read at a "
    "glance. Write 1 to 3 short sentences (about 300 characters max) on the CURRENT "
    "state of the work.\n\n"
    "Anchor on the most recent substantive task or problem — not on a trailing meta "
    "turn (a slash command, a request to run tests / verify / commit, or an "
    "acknowledgement like 'ok' or 'go ahead'). Scan back to the real work item and "
    "anchor there.\n\n"
    "Open with the work: 'Fixing ...', 'Investigating ...', 'Building ...', "
    "'Refactoring ...', or a noun-phrase headline. Do not open with 'The user "
    "asked ...' and do not narrate as the agent ('I have ...').\n\n"
    "Preserve the session's distinctive nouns exactly — file names, symbols, error "
    "strings, commands, product or library names, numbers.\n\n"
    "Use the RECENT ACTIVITY actions to ground what was actually done. State what is "
    "done or found, and any unresolved, blocked, or failed piece. Do not claim the "
    "work is complete unless the transcript explicitly says so, and do not invent "
    "next steps.\n\n"
    "Output plain sentences only — no lists, no numbering, no bullets, no preamble, "
    "no quoting."
)
# Appended on the single retry when the first reply came back list/bullet-shaped.
SUMMARY_RETRY_PROMPT = (
    SUMMARY_PROMPT
    + "\n\nYour previous reply was rejected for using a list, numbering, or bullets. "
    "Reply with 1 to 3 plain sentences only."
)
TRANSCRIPT_MAX_CHARS = 60_000
SUMMARY_MAX_CHARS = 320
# Recent tool/agent calls appended to the transcript so the model can ground the
# "current status" in what the session actually did, not just what was said.
ACTIONS_HEADER = "--- RECENT ACTIVITY (oldest first) ---"
ACTIONS_MAX_COUNT = 40
ACTION_LINE_MAX = 160
ACTIONS_BUDGET_CHARS = 12_000
_NUMBER_PREFIX = re.compile(r"^\s*\d+[.)]\s+")
_BULLET_PREFIX = re.compile(r"^\s*[-*•]\s+")
_URL = re.compile(r"https?://\S+")
CACHE_VERSION = 1
PRUNE_AFTER_DAYS = 30


@dataclass
class SummaryEntry:
    summary: str
    generated_at: str
    source_last_event_at: str


def load_cache(path: Path = SUMMARIES_PATH) -> dict[str, SummaryEntry]:
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    entries = payload.get("entries") or {}
    out: dict[str, SummaryEntry] = {}
    for k, v in entries.items():
        if not isinstance(v, dict):
            continue
        try:
            out[k] = SummaryEntry(
                summary=v["summary"],
                generated_at=v["generated_at"],
                source_last_event_at=v.get("source_last_event_at", ""),
            )
        except KeyError:
            continue
    return out


def write_cache(cache: dict[str, SummaryEntry], path: Path = SUMMARIES_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": CACHE_VERSION,
        "entries": {k: asdict(v) for k, v in cache.items()},
    }
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".summaries-", suffix=".json")
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


def prune_cache(
    cache: dict[str, SummaryEntry],
    max_age_days: int = PRUNE_AFTER_DAYS,
    now: float | None = None,
) -> int:
    """Drop entries whose JSONL is gone or untouched for > max_age_days.

    Keyed by session path, the cache otherwise grows unbounded: closed
    sessions linger forever. Ages by the JSONL's mtime (real activity) rather
    than the summary's generated_at, so a long-lived but active session is
    never pruned. Mutates `cache` in place; returns the number removed.
    """
    cutoff = (now if now is not None else time.time()) - max_age_days * 86400
    stale: list[str] = []
    for path in cache:
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            stale.append(path)  # JSONL gone
            continue
        if mtime < cutoff:
            stale.append(path)
    for path in stale:
        del cache[path]
    return len(stale)


def drain_regen_requests(path: Path = REGEN_REQUESTS_PATH) -> set[str]:
    if not path.exists():
        return set()
    tmp = path.with_suffix(path.suffix + ".draining")
    try:
        os.replace(path, tmp)
    except OSError:
        return set()
    try:
        text = tmp.read_text()
    except OSError:
        text = ""
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass
    return {line.strip() for line in text.splitlines() if line.strip()}


def _render_action(payload: dict) -> str | None:
    """Render one function_call payload as a terse one-line activity entry."""
    name = payload.get("name")
    if not name:
        return None
    args = payload.get("arguments")
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except (json.JSONDecodeError, ValueError):
            args = {}
    if not isinstance(args, dict):
        args = {}
    if name == "exec_command":
        cmd = " ".join((args.get("cmd") or "").split())
        return f"exec: {cmd}" if cmd else None
    if name == "spawn_agent":
        atype = args.get("agent_type") or "?"
        msg = " ".join((args.get("message") or "").split())
        return f"spawn_agent({atype}): {msg}" if msg else f"spawn_agent({atype})"
    return name


def _compose_transcript(messages: list[str], actions: list[str], max_chars: int) -> str:
    """Join messages with a trailing RECENT ACTIVITY block, within the char budget.

    Actions are appended last (recency) so the model can ground the "current
    status" in what the session actually did. Messages get whatever budget the
    actions block leaves and are tail-truncated, as before.
    """
    actions_block = ""
    if actions:
        recent = [a[:ACTION_LINE_MAX] for a in actions[-ACTIONS_MAX_COUNT:]]
        body = "\n".join(recent)
        if len(body) > ACTIONS_BUDGET_CHARS:
            body = body[-ACTIONS_BUDGET_CHARS:]
        actions_block = f"\n\n{ACTIONS_HEADER}\n{body}"
    msg_budget = max(0, max_chars - len(actions_block))
    msg_text = "\n".join(messages)
    if len(msg_text) > msg_budget:
        msg_text = msg_text[-msg_budget:]
    return (msg_text + actions_block).strip()


def extract_transcript(session_path: str, max_chars: int = TRANSCRIPT_MAX_CHARS) -> str:
    """Return user/agent messages + a recent-activity block, tail-truncated."""
    try:
        with open(session_path, "rb") as f:
            raw = f.read()
    except OSError:
        return ""
    messages: list[str] = []
    actions: list[str] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            ev = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        payload = ev.get("payload") or {}
        ptype = payload.get("type")
        if ev.get("type") == "event_msg":
            if ptype == "user_message":
                msg = payload.get("message")
                if isinstance(msg, str) and msg:
                    messages.append(f"USER: {msg}")
            elif ptype == "agent_message":
                msg = payload.get("message")
                if isinstance(msg, str) and msg:
                    messages.append(f"AGENT: {msg}")
        elif ptype == "function_call":
            rendered = _render_action(payload)
            if rendered:
                actions.append(rendered)
    return _compose_transcript(messages, actions, max_chars)


def _looks_malformed(line: str) -> bool:
    """True if the reply is list/bullet-shaped instead of plain sentences.

    URLs are not flagged: a recap may legitimately mention a path or link, and
    _sanitize strips them anyway — no point burning the single retry on it.
    """
    return bool(_NUMBER_PREFIX.match(line) or _BULLET_PREFIX.match(line))


def _sanitize(line: str, max_chars: int = SUMMARY_MAX_CHARS) -> str:
    """Strip residual numbering/bullets/URLs, collapse to one paragraph, cap length.

    Caps on a word boundary so an over-long recap ends cleanly with an ellipsis
    instead of a chopped-off word/backtick. Final safety net after the model.
    """
    line = _NUMBER_PREFIX.sub("", line)
    line = _BULLET_PREFIX.sub("", line)
    line = _URL.sub("", line)
    text = " ".join(line.split())
    if len(text) <= max_chars:
        return text
    cut = text[: max_chars - 1]
    if " " in cut:
        cut = cut[: cut.rfind(" ")]
    return cut.rstrip(" ,;:—-`(") + "…"


def _run_codex_summary(session_path: str, transcript: str, prompt: str) -> str | None:
    """One codex exec pass. Returns the stripped first output line, or None."""
    fd, out_path = tempfile.mkstemp(prefix="triage-summary-", suffix=".txt")
    os.close(fd)
    try:
        try:
            subprocess.run(
                [
                    "codex", "exec",
                    "-m", SUMMARY_MODEL,
                    "--ephemeral",
                    "--skip-git-repo-check",
                    "-s", "read-only",
                    "-o", out_path,
                    prompt,
                ],
                input=transcript,
                text=True,
                capture_output=True,
                timeout=SUMMARY_TIMEOUT_SEC,
                check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            log.warning("summary failed for %s: %s", session_path, exc)
            return None
        try:
            text = Path(out_path).read_text().strip()
        except OSError:
            return None
        if not text:
            return None
        # Return the full reply; _sanitize collapses newlines into one paragraph.
        return text
    finally:
        try:
            Path(out_path).unlink()
        except OSError:
            pass


def generate_summary_blocking(session_path: str) -> str | None:
    """Run codex exec to summarise the session. Returns None on any failure.

    The model occasionally ignores the one-line instruction and emits a
    numbered plan or a line with a URL. When the first reply is list/URL-shaped
    we retry once with a corrective prompt, then sanitize as a final guard.
    """
    transcript = extract_transcript(session_path)
    if not transcript:
        return None
    line = _run_codex_summary(session_path, transcript, SUMMARY_PROMPT)
    if line is None:
        return None
    if _looks_malformed(line):
        retry = _run_codex_summary(session_path, transcript, SUMMARY_RETRY_PROMPT)
        if retry is not None:
            line = retry
    cleaned = _sanitize(line)
    return cleaned or None


class SummaryManager:
    """Submit summary jobs to a thread pool; drain completions on each tick."""

    def __init__(self, max_workers: int = 2) -> None:
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="summary")
        # session_path → (future, source_last_event_at)
        self._in_flight: dict[str, tuple[Future[str | None], str]] = {}
        # session_path → source_last_event_at of the most recent attempt.
        # Remembered even after a failed (None) result so the watcher's
        # auto-regen guard does not re-submit the same failing job every tick.
        self._attempted: dict[str, str] = {}

    def submit(self, session_path: str, source_last_event_at: str) -> bool:
        if session_path in self._in_flight:
            return False
        fut = self._pool.submit(generate_summary_blocking, session_path)
        self._in_flight[session_path] = (fut, source_last_event_at)
        self._attempted[session_path] = source_last_event_at
        return True

    def attempted(self, session_path: str, source_last_event_at: str) -> bool:
        """True if a job for this exact completion point was already attempted."""
        return self._attempted.get(session_path) == source_last_event_at

    def drain_completed(self) -> list[tuple[str, str, str | None]]:
        out: list[tuple[str, str, str | None]] = []
        for path in list(self._in_flight):
            fut, src_at = self._in_flight[path]
            if not fut.done():
                continue
            del self._in_flight[path]
            try:
                summary = fut.result()
            except Exception:
                log.exception("summary job raised for %s", path)
                summary = None
            out.append((path, src_at, summary))
        return out

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)
