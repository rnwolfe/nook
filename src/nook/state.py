"""Cross-process state under $XDG_STATE_HOME/nook/ (default ~/.local/state/nook/).

An agent spawns a FRESH PROCESS per call, so throttle timers, the circuit-breaker window, and
the scraped api-key/persisted-hash cache must live on disk, not in memory (contract §12). This
module is a tiny file-locked JSON KV store; throttle.py and keyhash.py build on it.
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


def state_dir() -> Path:
    if p := os.environ.get("NOOK_STATE_DIR"):
        base = Path(p)
    else:
        xdg = os.environ.get("XDG_STATE_HOME")
        root = Path(xdg) if xdg else Path.home() / ".local" / "state"
        base = root / "nook"
    base.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(base, 0o700)
    except OSError:
        pass
    return base


def _path(name: str) -> Path:
    return state_dir() / name


@contextmanager
def _locked(name: str) -> Iterator[Path]:
    """Advisory exclusive lock via a sidecar lockfile, so concurrent nook processes serialize
    their read-modify-write of a state file. Falls back to no-op locking where fcntl is absent."""
    lock_path = _path(name + ".lock")
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_EX)
        except (ImportError, OSError):
            pass
        yield _path(name)
    finally:
        try:
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_UN)
        except (ImportError, OSError):
            pass
        os.close(fd)


def read_json(name: str, default: Any = None) -> Any:
    p = _path(name)
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text() or "null")
    except (json.JSONDecodeError, OSError):
        return default


def write_json(name: str, value: Any) -> None:
    p = _path(name)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False))
    os.chmod(tmp, 0o600)
    os.replace(tmp, p)  # atomic


@contextmanager
def update_json(name: str, default: Any) -> Iterator[list]:
    """Locked read-modify-write. Yields a one-element list holding the current value; assign back
    to element 0 to persist. Serialized across processes by the sidecar lock."""
    with _locked(name):
        box = [read_json(name, default)]
        try:
            yield box
        finally:
            write_json(name, box[0])
