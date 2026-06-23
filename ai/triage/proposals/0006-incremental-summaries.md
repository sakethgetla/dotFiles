# 0006 — Incremental summaries

- **Tier:** 2 · **Effort:** M · **Status:** idea

## Summary

Summarise only new turns since the last summary instead of re-sending the whole transcript on every `task_complete`.

## Motivation

- `extract_transcript` sends up to 60K chars of user/agent messages **every** regen.
- Cost and latency scale with session length; long sessions re-pay for old context each turn.
- README v2 explicitly flags this as the next summaries improvement.

## Design

- Cache per session: `last_summary` + `last_offset` (byte offset or last event timestamp summarised).
- On regen, extract only turns after `last_offset`.
- Prompt = `prior summary + new turns → updated one-liner`.
- Fall back to full-transcript summary when no prior summary exists.

```
SummaryEntry += last_offset
regen:
   new = transcript_since(last_offset)
   prompt = "Prior: <last_summary>\nNew turns:\n<new>\n→ updated one-liner"
   store(summary, last_offset = end)
```

## Touchpoints

- `summaries.py`: extend `SummaryEntry`; `extract_transcript(since=...)`; new prompt; update `generate_summary_blocking`.
- No watcher/dashboard change beyond passing the prior summary into the job.

## Effort

- Medium. Mostly within `summaries.py`. Needs care that offsets stay valid across compaction (`context_compacted` events).

## Open questions

- Offset by byte vs by last-event timestamp? Timestamp is robust to file rewrites.
- Reset to full summary after `context_compacted`?
