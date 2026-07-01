"""Cross-process self-throttle + circuit-breaker (contract §12).

nook is a guest on Airbnb's infrastructure and an agent will call it in tight, unattended loops.
Two protections, both persisted to disk (state.py) because each call is a fresh process:

- **Throttle**: enforce a minimum spacing between requests (jittered) so we make fewer, slower,
  honest requests than a person clicking around. Reduce volume — never disguise it.
- **Circuit-breaker**: when Airbnb returns a block/challenge (403 / 429 / CAPTCHA), trip a breaker
  for a cooldown window and FAIL FAST (exit 7) instead of retrying into the block. Waiting is
  opt-in (`--wait`). Retrying into a block is both rude and counterproductive.

Deterministic randomness note: jitter uses `random`, seeded per-process; it only affects sleep
duration, never correctness.
"""

from __future__ import annotations

import random
import time

from .errors import rate_limited
from .state import update_json

# Conservative defaults — a single user planning a trip, not a scraper.
MIN_INTERVAL_S = 1.0        # ~1 request/second
JITTER_S = 0.4              # +[0,0.4)s so we're not metronomic
BREAKER_COOLDOWN_S = 900    # 15 min after a block before we probe again

_THROTTLE_FILE = "throttle.json"
_BREAKER_FILE = "breaker.json"


def _now() -> float:
    return time.time()


def breaker_state() -> dict:
    """Current circuit-breaker view for `doctor` (does not mutate)."""
    from .state import read_json

    b = read_json(_BREAKER_FILE, {}) or {}
    until = float(b.get("blocked_until", 0))
    return {"tripped": _now() < until, "until": until,
            "reason": b.get("reason"), "remaining_s": max(0, round(until - _now()))}


def trip_breaker(reason: str, retry_after_s: float | None = None) -> None:
    """Open the breaker for a cooldown window after a block/challenge."""
    cooldown = retry_after_s if (retry_after_s and retry_after_s > 0) else BREAKER_COOLDOWN_S
    with update_json(_BREAKER_FILE, {}) as box:
        box[0] = {"blocked_until": _now() + cooldown, "reason": reason, "tripped_at": _now()}


def _check_breaker(wait: bool, max_wait_s: float) -> None:
    """Raise rate_limited (fail-fast) if the breaker is open, unless `wait` and the remaining
    cooldown fits inside max_wait_s (then block until it clears)."""
    from .state import read_json

    b = read_json(_BREAKER_FILE, {}) or {}
    until = float(b.get("blocked_until", 0))
    remaining = until - _now()
    if remaining <= 0:
        return
    if wait and remaining <= max_wait_s:
        time.sleep(remaining)
        return
    err = rate_limited(f"circuit breaker open for {round(remaining)}s "
                       f"(reason: {b.get('reason', 'block')})")
    # Let an agent schedule its own retry.
    err.remediation = (f"wait ~{round(remaining)}s and retry at lower volume "
                       f"(or pass --wait to block); nook will not evade the block")
    raise err


def _apply_spacing() -> None:
    """Sleep just long enough to honor MIN_INTERVAL_S since the last request (cross-process)."""
    target = MIN_INTERVAL_S + random.random() * JITTER_S
    with update_json(_THROTTLE_FILE, {}) as box:
        last = float((box[0] or {}).get("last_request", 0))
        wait = last + target - _now()
        if wait > 0:
            time.sleep(wait)
        box[0] = {"last_request": _now()}


def before_request(wait: bool = False, max_wait_s: float = 0.0) -> None:
    """Call immediately before every upstream request: enforce the breaker, then space the call."""
    _check_breaker(wait=wait, max_wait_s=max_wait_s)
    _apply_spacing()
