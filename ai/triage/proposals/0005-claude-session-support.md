# 0005 — Claude session support

- **Tier:** 2 · **Effort:** M · **Status:** idea

## Summary

Track Claude Code sessions alongside codex. Same architecture; only the JSONL dialect and process name differ.

## Motivation

- README known-limitation: Claude unsupported, but "architecture is identical".
- Running both codex and Claude in kitty tabs is common → triage should see both.

## Design

- **Process detection:** `find_codex_in_foreground` currently matches basename `codex`. Generalise to detect agent type and return `(pid, kind)` where `kind ∈ {codex, claude}`.
- **JSONL discovery:** codex → `~/.codex/sessions/*.jsonl`; Claude → its own transcript dir/format.
- **Classifier dispatch:** Claude's JSONL has a different lifecycle vocabulary → a second `classify_claude()`; pick by `kind`.
- `SessionRow` gains a `kind` field for display.

```
find agent in fg → (pid, kind)
   kind=codex  → jsonl under ~/.codex   → classify_codex
   kind=claude → jsonl under <claude>   → classify_claude
```

## Touchpoints

- `codex.py` → generalise to `agents.py` (or add detectors); keep `lsof` correlation shared.
- `classifier.py`: add Claude lifecycle rules (verify vocabulary empirically, like the codex table).
- `state.py`: `SessionRow.kind`.
- `summaries.py`: transcript extraction needs a per-dialect parser.
- `dashboard.py`: show kind badge.

## Effort

- Medium. The correlation/aggregation/marking layers are reusable; the new work is one parser + one classifier + dispatch.

## Open questions

- Where does Claude Code write its session transcript, and what is its lifecycle-event vocabulary? (needs empirical verification before coding)
- Does the summary prompt/model need to differ per agent?
