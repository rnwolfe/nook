---
title: Rate-limited (exit 7)
description: What exit 7 means, why the circuit breaker opens, and why the right move is to back off — not retry.
---

Exit `7` (`RATE_LIMITED`) means Airbnb returned a block or bot-challenge, and nook's circuit
breaker is now open. This page explains what trips it, why nook refuses to retry through it, and
what to actually do about it.

## What triggers it

Every network call goes through `transport.py`, which classifies each response before nook ever
sees the body:

- **HTTP 403 or 429** — an explicit block.
- **A 200 response that is secretly a challenge page** — the body is scanned for anti-bot
  markers (`px-captcha`, `perimeterx`, "Press & Hold", "Access to this page has been denied", and
  similar). Airbnb's edge (PerimeterX) sometimes returns 200 with an HTML interstitial instead of
  JSON, so nook checks the body, not just the status code.
- **A 200 that isn't valid JSON at all** — nook re-checks that body for challenge markers too. If
  it looks like a block, it's treated as one; otherwise it's reported as [upstream
  drift](/troubleshooting/upstream-drift/) instead (a shape change, not a block).

Any of these calls `trip_breaker()`, which writes `{blocked_until, reason, tripped_at}` to
`$XDG_STATE_HOME/nook/breaker.json`. The cooldown is whatever `Retry-After` Airbnb sent, or 15
minutes (900s) if there wasn't one. That file is the only reason this works across an agent's
one-process-per-call loop — there's no long-lived daemon to hold a timer in memory.

Once the breaker is open, **every subsequent call** — even to a totally different command or
listing — checks it first and fails immediately with exit `7`, before making any HTTP request at
all. You don't need to hit the block again to find out you're still blocked.

## Why nook fails fast instead of retrying

This is deliberate, not a missing feature. From the source:

> Circuit-breaker: when Airbnb returns a block/challenge (403 / 429 / CAPTCHA), trip a breaker
> for a cooldown window and FAIL FAST (exit 7) instead of retrying into the block... Retrying
> into a block is both rude and counterproductive.

Retrying into an active block just confirms to Airbnb's edge that this client is automated and
persistent — the opposite of what you want. Contrast this with the *other* failure family, exit
`8` ([retryable](/reference/exit-codes/)): transient 5xx responses and network errors get a
short bounded retry (2 attempts, exponential backoff) because those are genuinely safe to retry.
A block is not in that category, ever — nook will not silently convert a 403 into a retry loop no
matter how it's invoked.

The error message nook prints tells you exactly this:

```json
{
  "error": "blocked by Airbnb (rate limit or bot challenge): HTTP 429",
  "code": "RATE_LIMITED",
  "remediation": "stop and retry later at lower volume; nook self-throttles and will not evade the block"
}
```

If the breaker was already open when you called (rather than this call being the one that
tripped it), you'll instead see how much cooldown is left:

```json
{
  "error": "circuit breaker open for 612s (reason: HTTP 429)",
  "code": "RATE_LIMITED",
  "remediation": "wait ~612s and retry at lower volume (or pass --wait to block); nook will not evade the block"
}
```

## `--wait` / `--max-wait`

Every network-hitting command (`search`, `place search`, `listing get`, `availability`,
`reviews`) accepts two flags for this exact situation:

```bash
nook availability abc123 --wait
nook availability abc123 --wait --max-wait 300
```

- `--wait` — if the breaker is open, block and sleep out the remaining cooldown instead of
  failing fast, then proceed with the call once it clears.
- `--max-wait SECONDS` (default `900`) — a cap on how long `--wait` is allowed to sleep. If the
  remaining cooldown is longer than `--max-wait`, nook does **not** wait — it still fails fast
  with exit `7`, same as without `--wait`.

`--wait` is opt-in for a reason: an agent looping tightly should feel the backpressure by
default (fail fast, decide what to do next) rather than silently stalling for up to 15 minutes.
Reach for `--wait` when you specifically want a single call to ride out a short, known cooldown —
for example, a script that expects occasional throttling and would rather block once than handle
a retry loop itself.

## Checking breaker state with `doctor`

`nook doctor` reports the breaker's current state without making any network request:

```bash
nook doctor --json
```

```json
{
  "error": "one or more checks failed",
  "code": "DOCTOR_FAILED",
  "remediation": "see the failing check's detail"
}
```

When every check passes, `doctor` prints `{"ok": true, "checks": [...], "legitimacy": "..."}`
directly to stdout — note this is `doctor`'s own shape, not the `schemaVersion`/`scope`/`data`
read envelope described in [Output envelope](/concepts/output-envelope/) (that envelope is only
for `search`/`listing get`/`availability`/`reviews`/`place search`). A closed breaker looks like:

```json
{ "name": "circuit_breaker", "ok": true, "detail": "closed" }
```

Note the asymmetry: `doctor` itself exits `10` (`CONFIG`, `DOCTOR_FAILED`) when the breaker is
tripped (or any other check fails) — not `7`. `doctor` is a diagnostic snapshot ("is everything
healthy right now"), not a network call subject to the breaker itself.

One current rough edge: when the breaker (or any check) is tripped, `doctor` exits `10` with only
the generic `{"error": "one or more checks failed", "code": "DOCTOR_FAILED", "remediation": "see
the failing check's detail"}` above — the per-check `checks` array (which would otherwise show
`circuit_breaker`'s `remaining_s`-style detail, e.g. `"tripped — 612s cooldown remaining (HTTP
429)"`) is only emitted on the success path, so that detail isn't actually surfaced when it's the
thing you'd want to see. Until that's tightened up, if you hit exit `7` and want the exact
cooldown remaining, the error message from the command that tripped or hit the breaker (the
`circuit breaker open for Ns` message shown above) is the reliable source — `doctor` will only
confirm *that* something is unhealthy, not which check or its detail.

## The guidance: reduce volume, don't evade

nook's whole backend posture (contract §12) is: present the same TLS/JA3 fingerprint and public
API key the real Airbnb web client uses — that's matching the genuine client, not disguising
one — and self-throttle to roughly one request per second, jittered, tracked cross-process in
`$XDG_STATE_HOME/nook/`. There are no proxies, no IP rotation, no CAPTCHA solving, and nothing in
nook will ever try to route around a block.

So if you're hitting exit `7`:

1. **Stop.** Don't loop calling the same or other nook commands hoping one slips through — the
   breaker blocks all of them until it clears, and hammering it looks worse to Airbnb's edge, not
   better.
2. **Reduce volume.** If you were running a tight batch (many listings, many searches back to
   back), that's very likely what tripped it. Space calls out, cut concurrency, or use
   [pagination](/guides/pagination/) and [`--limit`](/reference/flags/) to ask for less per call.
3. **Wait it out** — either manually (the `circuit breaker open for Ns` message on the call that
   hit the breaker tells you exactly how long) or with `--wait --max-wait N` on the next call.
4. **Do not try to evade it.** No amount of header spoofing, retry cleverness, or "just try once
   more" is a supported or intended use of this tool. If Airbnb blocks nook, the correct response
   is to stop, not to route around it.

See [Legitimacy](/concepts/legitimacy/) and [Etiquette](/concepts/etiquette/) for the fuller
reasoning behind this posture, and [Exit codes](/reference/exit-codes/) for how `7` relates to
the other failure exits.
