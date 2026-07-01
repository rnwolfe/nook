---
title: Backend etiquette & the circuit-breaker
description: nook self-throttles, presents the real client honestly, and circuit-breaks on a block instead of retrying into it.
---

nook self-throttles with cross-process state and circuit-breaks on a block (403 challenge / 429 / CAPTCHA) rather than retrying into it — you get exit `7` (`RATE_LIMITED`). It presents the real web client's fingerprint at low volume: no proxies, no IP rotation, no CAPTCHA solving. Reduce volume, don't disguise identity.

<!-- TODO(harvest-docs): the throttle model, cross-process state, the circuit-breaker, --wait, and the "no evasion" stance in full. -->
