---
title: Rate-limited (exit 7)
description: What exit 7 means, why the circuit breaker opens, and why the right move is to back off — not retry.
---

Exit `7` (`RATE_LIMITED`) means upstream throttled or blocked this client and nook's circuit breaker has opened. Do not loop on it — back off. `--wait` opts into blocking until the throttle window clears.

<!-- TODO(harvest-docs): diagnosing exit 7, the breaker lifecycle, --wait, and the "stop, don't evade" response. -->
