---
title: Backend etiquette & the circuit-breaker
description: nook self-throttles, presents the real client honestly, and circuit-breaks on a block instead of retrying into it.
---

nook talks to Airbnb's internal `/api/v3` GraphQL API — the same one the airbnb.com web app
calls. There's no public, documented, stable API for search or availability, so nook behaves like
the real client, at low volume, and stops the instant Airbnb pushes back. This page is the "how"
and "why" behind that stance: TLS fingerprinting, throttling, the circuit-breaker, and what
happens when you get blocked.

## Presenting the real client, not evading detection

Airbnb's edge (a bot-management layer — HUMAN/PerimeterX-style) fingerprints the TLS handshake
itself. A plain Python `requests` or `httpx` client has a different TLS/JA3 fingerprint than a
real browser, so it gets 403'd before a single byte of your request matters.

nook uses [`curl_cffi`](https://github.com/yifeikong/curl_cffi) with `impersonate="chrome124"`
(`src/nook/transport.py`), which presents the **same TLS/JA3 fingerprint a real Chrome 124
client sends**. That's the whole trick, and it's worth being precise about what it is and isn't:

- **It is**: matching the wire-level fingerprint of the genuine web client that every visitor to
  airbnb.com already uses.
- **It is not**: proxy rotation, IP masking, residential-proxy pools, or CAPTCHA-solving
  services. nook has none of that. There's no proxy configuration anywhere in the codebase.

nook also uses Airbnb's own **public** static API key (see [Public key + persisted-hash
self-heal](#public-key--persisted-hash-self-heal) below) — the same key the SPA ships to every
anonymous visitor's browser. Nothing here is stolen, brute-forced, or reverse-engineered out of a
private channel. It's the public contract of the public web page, called directly instead of
through a browser.

The house rule, verbatim from the code (`transport.py`):

> "match the genuine client, don't disguise identity."

## Cross-process throttle

An agent calling nook typically spawns a **fresh process per invocation** — there's no long-lived
daemon holding an in-memory rate limiter. If nook kept its throttle state in memory, an agent
looping `nook availability 123` in a tight `for` loop would reset the clock every single call and
the throttle would be a no-op.

So the throttle lives on disk, under `$XDG_STATE_HOME/nook/` (default
`~/.local/state/nook/`, override with `NOOK_STATE_DIR`), as small JSON files guarded by an
advisory file lock (`src/nook/state.py`). Every process — regardless of which nook subcommand
invoked it — reads and writes the same `throttle.json`, so pacing is enforced *across* processes,
not just within one.

Before every upstream request (`throttle.before_request`, in `src/nook/throttle.py`):

- **Minimum spacing**: nook waits at least `MIN_INTERVAL_S` (1.0s) since the last request,
  plus jitter of `[0, JITTER_S)` (0 to 0.4s), so calls land around **~1 request/second**,
  not metronomically. That's the interval a single person clicking around would produce —
  not a scraper's.
- **This reduces volume. It does not disguise identity.** nook doesn't rotate identities to get
  around a limit; it just makes fewer, slower, honest requests.

## The circuit-breaker: fail fast, never retry into a block

If Airbnb responds with a block or a bot challenge, retrying immediately is both rude (you're
hammering an edge that just told you to stop) and useless (you'll get blocked again). nook's
transport layer classifies a response as *challenged* (`transport._looks_challenged`) when:

- the HTTP status is `403` or `429`, or
- a `200` response body contains an anti-bot interstitial marker instead of real JSON — nook
  checks the first 2KB of the body for markers like `px-captcha`, `captcha-container`,
  `Press & Hold`, `_pxhc`, `perimeterx`, or `Access to this page has been denied`.

On a match, nook **trips the circuit-breaker** (`throttle.trip_breaker`) and immediately raises a
`RATE_LIMITED` error — exit code `7` — instead of retrying:

```bash
$ nook search "Lisbon" --checkin 2026-08-01 --checkout 2026-08-05
```
```json
{"error": "blocked by Airbnb (rate limit or bot challenge): circuit breaker open for 900s (reason: HTTP 429)",
 "code": "RATE_LIMITED",
 "remediation": "wait ~900s and retry at lower volume (or pass --wait to block); nook will not evade the block"}
```
Process exits `7`.

The breaker's open/closed state — like the throttle clock — is written to
`$XDG_STATE_HOME/nook/breaker.json`, so it's honored across every subsequent process, not just
the one that got blocked. Once tripped, **every nook call fails fast with exit 7 immediately**,
without even attempting a request, until the cooldown clears. `nook doctor` surfaces the live
breaker state (tripped/until/reason/remaining_s) without mutating it, so an agent can check
before deciding whether to retry.

**Cooldown window**: 15 minutes (`BREAKER_COOLDOWN_S = 900`) by default — unless Airbnb sent a
`Retry-After` header, in which case nook honors that value instead (parsed as seconds in
`transport._handle_block`).

Retrying into a fresh block extends nothing and proves nothing except that the agent is willing
to abuse a host that just told it to stop. nook won't do that on your behalf.

### Opting into waiting: `--wait` / `--max-wait`

Every network command accepts `--wait` and `--max-wait SECONDS` (default `900`). By default nook
**fails fast** — if the breaker is open, or your calls are outrunning the throttle, you get an
immediate answer (success, or exit 7) rather than a command that silently blocks. Pass `--wait` to
opt into blocking instead:

```bash
nook availability 12345678 --months 2 --wait --max-wait 300
```

With `--wait`, if the breaker's remaining cooldown fits inside `--max-wait`, nook sleeps out the
remainder and then proceeds — no retry-into-a-block, just a bounded, honest pause. If the
remaining cooldown is *longer* than `--max-wait`, nook still fails fast with exit `7` rather than
blocking indefinitely; it's a cap, not a guarantee.

`5xx` responses and network errors are handled separately from blocks: those are genuinely
transient, so `transport.py` retries them up to twice with exponential backoff before surfacing
`RETRYABLE` (exit `8`) — this is the one case nook *does* retry, because it isn't a block.

## Public key + persisted-hash self-heal

Airbnb's own web app authenticates to its `/api/v3` GraphQL endpoint with a **public, static API
key** — the same key value is embedded in the HTML shipped to every anonymous visitor. nook
scrapes that key from the airbnb.com homepage (`src/nook/keyhash.py`), caches it in
`$XDG_STATE_HOME/nook/keyhash.json` with a 24-hour TTL, and falls back to a long-stable known
public value (`d306zoyjsyarp7ifhu67rjxn52tv0t20`) if the live scrape misses. There's no secret
here to protect or extract — it's public by construction, shipped to anyone who loads the page.

Each GraphQL operation nook calls (`StaysSearch` for search, `PdpAvailabilityCalendar` for
availability, `StaysPdpReviewsQuery` for reviews) is a **persisted query** identified by a sha256
hash. (`nook listing get` doesn't call a GraphQL operation at all — it parses the PDP page's
embedded state HTML instead; `keyhash.py` also carries a known-good `StaysPdpSections` hash, but
`client.py` doesn't reference it today.) Most of the GraphQL hashes are stable; `StaysSearch`'s
hash rotates when Airbnb ships a new web bundle.
When a search call gets a `PersistedQueryNotFound`-shaped failure, nook re-scrapes the current
hash from the JS entry bundle and retries once. If that self-heal also fails, nook doesn't guess
or hammer the endpoint further — it raises `UPSTREAM_DRIFT` (exit `20`), which tells you (or your
agent) that Airbnb changed something structural and nook likely needs a code update, not a retry
or a backoff. See [Upstream drift](/troubleshooting/upstream-drift/) for what to do when you hit
it.

## Why this matters for agents

If you're driving nook from an agent loop:

- **Don't retry exit `7` yourself.** The breaker is already open; hammering it just extends the
  block for whatever comes next. Either back off for the reported duration, or pass `--wait
  --max-wait N` and let nook manage the pause.
- **Exit `20` is not exit `7`.** A block (`7`) means "you're being rate-limited or challenged,
  slow down." Drift (`20`) means "the API shape or a persisted hash changed out from under us,"
  which self-resolves only with a nook update.
- **State is shared across your whole agent session.** Every nook invocation — even from
  different subcommands — reads and writes the same throttle/breaker files, so pacing is
  consistent no matter how many separate calls you fire.

## See also

- [Read-only by design](/concepts/read-only/) — why mutation flags exist but do nothing.
- [Legitimacy boundary](/concepts/legitimacy/) — the legal and ToS posture behind reading public
  logged-out pages.
- [Rate limited](/troubleshooting/rate-limited/) — what to do when you hit exit `7`.
- [Upstream drift](/troubleshooting/upstream-drift/) — what to do when you hit exit `20`.
