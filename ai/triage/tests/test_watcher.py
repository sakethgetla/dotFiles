from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from triage.watcher import acquire_singleton_lock


def test_singleton_lock_blocks_second_acquire(tmp_path):
    lock = tmp_path / "watcher.lock"
    first = acquire_singleton_lock(lock)
    assert first is not None
    # A second attempt while the first holds the flock must fail.
    assert acquire_singleton_lock(lock) is None
    first.close()  # releasing the fd releases the flock
    # Re-acquirable once released (covers crash-recovery: OS frees the lock).
    third = acquire_singleton_lock(lock)
    assert third is not None
    third.close()


def test_singleton_lock_writes_pid(tmp_path):
    lock = tmp_path / "watcher.lock"
    f = acquire_singleton_lock(lock)
    assert f is not None
    assert lock.read_text().strip() == str(os.getpid())
    f.close()
