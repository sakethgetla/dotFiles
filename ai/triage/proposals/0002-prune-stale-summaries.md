# 0002 — Prune stale summary cache

- **Tier:** 1 · **Effort:** S · **Status:** shipped

> Shipped: `summaries.prune_cache()` (ages by JSONL mtime, drops missing JSONLs), called once at `watcher.main()` startup. Resolved the open question in favour of mtime. Tests in `tests/test_summaries.py`.

## Summary

Drop `summaries.json` entries whose session JSONL no longer exists or is older than N days, at watcher startup.

## Motivation

- `summaries.json` is keyed by JSONL path and **never pruned** (README v2 admits this).
- Grows unbounded across reboots; closed sessions linger forever.

## Design

- At watcher start (or first tick), after `load_cache()`:
  - drop entries whose `session_path` no longer exists on disk;
  - drop entries whose `generated_at` is older than `PRUNE_AFTER_DAYS` (default 30).
- Write back once if anything changed.

```
load_cache()
  → for path, entry in cache:
       if not exists(path):           drop
       elif age(entry.generated_at) > 30d: drop
  → write_cache() if dirty
```

## Touchpoints

- `summaries.py`: add `prune_cache(cache, max_age_days)`.
- `watcher.main()`: call once before the tick loop.

## Effort

- Small. Pure function + one call site. Trivially unit-testable.

## Open questions

- Prune by JSONL mtime instead of `generated_at`? mtime better reflects real activity.
