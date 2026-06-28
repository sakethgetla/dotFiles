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
    "glance. You are given ONLY the user's own messages to a coding agent — their "
    "side of the conversation, not the agent's replies or actions.\n\n"
    "Output format — follow exactly:\n"
    "- The FIRST line must be `TITLE: <headline>` where the headline is at most 6 "
    "words, no trailing punctuation, naming the specific task (lead with a "
    "distinctive noun — a file, symbol, skill, or feature — so sibling sessions on "
    "the same area get different titles).\n"
    "- Then a blank line, then the summary body as plain sentences.\n\n"
    "Write up to 5 "
    "short sentences (about 500 characters max) describing the task the user is "
    "directing — what they are asking the agent to build, fix, or investigate.\n\n"
    "CRITICAL: only the FIRST sentence is reliably visible in the dashboard — the "
    "rest is clipped. The dashboard often holds several sessions on the same topic "
    "at once, so the first sentence must DISTINGUISH this session from a sibling on "
    "the same area. Lead with what makes THIS session unique — the specific "
    "sub-task, the skill or artifact in play, the layer or file being touched, the "
    "concrete current ask — never a generic topic line that could equally describe "
    "another session.\n\n"
    "Pack the first sentence with the distinctive nouns that set this session apart "
    "(file names, symbols, error strings, commands, skill names, product or library "
    "names, numbers). Do not defer them to later sentences that get clipped.\n\n"
    "Do NOT open with the shared source material — Slack or ticket links, thread "
    "IDs, the bare topic name — because sibling sessions usually cite the same "
    "sources and that makes their first sentences identical. Open instead with the "
    "specific deliverable, method, or angle the user wants (the skill invoked, the "
    "concrete question, the artifact or layer, what they want produced or tested), "
    "and mention the source links later if at all.\n\n"
    "Vary the opening: do NOT begin every recap with the same verb (e.g. always "
    "'Investigating ...'). A shared verb plus a shared topic noun makes sibling "
    "rows look identical. Open with the per-session differentiator, then a verb or "
    "noun-phrase headline as fits. Do not open with 'The user asked ...'.\n\n"
    "Anchor the current direction on the most recent substantive request — not on a "
    "trailing meta turn (a slash command, a request to run tests / verify / commit, "
    "or an acknowledgement like 'ok' or 'go ahead'). Scan back to the real work "
    "item. Lead with that concrete current direction, then in the following "
    "sentence(s) give the original goal and broader context from the earlier "
    "messages.\n\n"
    "Preserve the user's distinctive nouns exactly — file names, symbols, error "
    "strings, commands, product or library names, numbers.\n\n"
    "Describe what was asked, not whether it is done — you cannot see the agent's "
    "work, so do not claim anything is complete, fixed, or found, and do not invent "
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
SUMMARY_MAX_CHARS = 500
# Recent tool/agent calls appended to the transcript so the model can ground the
# "current status" in what the session actually did, not just what was said.
ACTIONS_HEADER = "--- RECENT ACTIVITY (oldest first) ---"
ACTIONS_MAX_COUNT = 40
ACTION_LINE_MAX = 160
ACTIONS_BUDGET_CHARS = 12_000
_NUMBER_PREFIX = re.compile(r"^\s*\d+[.)]\s+")
_BULLET_PREFIX = re.compile(r"^\s*[-*•]\s+")
_URL = re.compile(r"https?://\S+")
CACHE_VERSION = 2
PRUNE_AFTER_DAYS = 30
TITLE_MAX_CHARS = 48
_TITLE_LINE = re.compile(r"^\s*TITLE:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)


@dataclass
class SummaryEntry:
    summary: str
    generated_at: str
    source_last_event_at: str
    title: str = ""


def load_cache(path: Path = SUMMARIES_PATH) -> dict[str, SummaryEntry]:
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    # Drop the whole cache on a version mismatch. Older entries predate the
    # title field; rather than show blank titles until each session next gets a
    # user message, we discard them so the watcher regenerates everything.
    if payload.get("version") != CACHE_VERSION:
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
                title=v.get("title", ""),
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


def extract_user_messages(session_path: str, max_chars: int = TRANSCRIPT_MAX_CHARS) -> str:
    """Return only the user's messages from the session, tail-truncated.

    The summariser's input. Unlike extract_transcript (which also feeds search
    and includes agent messages + a recent-activity block), this is just the
    user's side of the conversation, so the recap anchors on the task the user
    is directing rather than narrating agent activity. Survives context
    compaction: the JSONL is append-only, so earlier user_message events remain
    in the file even past a context_compacted marker.
    """
    try:
        with open(session_path, "rb") as f:
            raw = f.read()
    except OSError:
        return ""
    messages: list[str] = []
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
        if payload.get("type") != "user_message":
            continue
        msg = payload.get("message")
        if isinstance(msg, str) and msg:
            messages.append(msg)
    text = "\n".join(messages)
    if len(text) > max_chars:
        text = text[-max_chars:]
    return text


def extract_recent_messages(
    session_path: str, max_messages: int = 40, max_bytes: int = 262_144
) -> list[tuple[str, str]]:
    """Return recent (role, text) pairs in chronological order.

    role is "you" for user_message events and "codex" for agent_message events;
    everything else (actions, reasoning, lifecycle) is ignored — this feeds the
    dashboard's preview popup, which shows just the conversation. Tail-reads the
    last max_bytes of the JSONL (dropping the partial first line) so it stays
    fast on multi-MB sessions. Consecutive same-role runs are collapsed to the
    last message of each run, so the result strictly alternates you/codex (a
    side often emits several messages per turn); then the last max_messages
    collapsed pairs are returned.
    """
    try:
        with open(session_path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            start = max(0, size - max_bytes)
            f.seek(start)
            raw = f.read()
    except OSError:
        return []
    lines = raw.splitlines()
    if start > 0 and lines:
        lines = lines[1:]  # drop the partial line the seek landed mid-way through
    pairs: list[tuple[str, str]] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            ev = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if ev.get("type") != "event_msg":
            continue
        payload = ev.get("payload") or {}
        ptype = payload.get("type")
        if ptype == "user_message":
            role = "you"
        elif ptype == "agent_message":
            role = "codex"
        else:
            continue
        msg = payload.get("message")
        if not (isinstance(msg, str) and msg):
            continue
        # Collapse a run of same-role messages to its last one so the preview
        # alternates you/codex rather than showing several bubbles from one side.
        if pairs and pairs[-1][0] == role:
            pairs[-1] = (role, msg)
        else:
            pairs.append((role, msg))
    return pairs[-max_messages:]


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


def _split_title_summary(text: str) -> tuple[str, str]:
    """Split a `TITLE: ...`-prefixed reply into (title, body).

    The model is asked to emit a `TITLE:` line then the summary. We find the
    first such line, take its text as the title, and treat everything else as
    the body. When no marker is present (the model ignored the format) the title
    is empty and the whole reply is the body; the caller derives a fallback
    title from the body so a row is never title-less.
    """
    m = _TITLE_LINE.search(text)
    if not m:
        return "", text.strip()
    title = m.group(1)
    body = (text[: m.start()] + text[m.end() :]).strip()
    return title, body


def _sanitize_title(title: str, max_chars: int = TITLE_MAX_CHARS) -> str:
    """Collapse a title to one tidy line, strip markup/quotes, cap length.

    Caps on a word boundary like _sanitize so it ends cleanly with an ellipsis
    rather than mid-word.
    """
    title = re.sub(r"(?i)^\s*TITLE:\s*", "", title)
    title = _URL.sub("", title)
    text = " ".join(title.split()).strip().strip("\"'`")
    if len(text) <= max_chars:
        return text.rstrip(" .,;:—-")
    cut = text[: max_chars - 1]
    if " " in cut:
        cut = cut[: cut.rfind(" ")]
    return cut.rstrip(" ,;:—-`(") + "…"


def _title_from_summary(summary: str, max_words: int = 6) -> str:
    """Fallback title: the first few words of the summary, tidied and capped."""
    words = summary.split()[:max_words]
    return _sanitize_title(" ".join(words))


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


def generate_summary_blocking(session_path: str) -> tuple[str, str] | None:
    """Run codex exec to summarise the session as (title, summary), or None.

    The model emits a `TITLE:` line then the summary body. We split the two
    apart, judge malformed-ness on the body (it occasionally ignores the
    plain-sentences instruction and emits a numbered plan), retry once if so,
    then sanitize title and body separately. If the model dropped the title
    line we derive one from the summary's opening so a row is never title-less.
    """
    transcript = extract_user_messages(session_path)
    if not transcript:
        return None
    reply = _run_codex_summary(session_path, transcript, SUMMARY_PROMPT)
    if reply is None:
        return None
    title, body = _split_title_summary(reply)
    if _looks_malformed(body):
        retry = _run_codex_summary(session_path, transcript, SUMMARY_RETRY_PROMPT)
        if retry is not None:
            title, body = _split_title_summary(retry)
    summary = _sanitize(body)
    if not summary:
        return None
    title = _sanitize_title(title) or _title_from_summary(summary)
    return title, summary


class SummaryManager:
    """Submit summary jobs to a thread pool; drain completions on each tick."""

    def __init__(self, max_workers: int = 2) -> None:
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="summary")
        # session_path → (future, source_last_event_at)
        self._in_flight: dict[str, tuple[Future[tuple[str, str] | None], str]] = {}
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

    def drain_completed(self) -> list[tuple[str, str, tuple[str, str] | None]]:
        """Return (session_path, source_last_event_at, (title, summary) | None)."""
        out: list[tuple[str, str, tuple[str, str] | None]] = []
        for path in list(self._in_flight):
            fut, src_at = self._in_flight[path]
            if not fut.done():
                continue
            del self._in_flight[path]
            try:
                result = fut.result()
            except Exception:
                log.exception("summary job raised for %s", path)
                result = None
            out.append((path, src_at, result))
        return out

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)
