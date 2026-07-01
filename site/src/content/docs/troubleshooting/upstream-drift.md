---
title: Upstream drift (exit 20)
description: When Airbnb changes its internals, nook returns exit 20 — distinct from a rate limit — and the fix is to update nook.
---

Exit `20` (`UPSTREAM_DRIFT`) means Airbnb changed something nook depends on to parse its
responses — a public API key, a persisted-query hash, or the shape of a JSON response — and
nook could not recover on its own. This is the one nook-specific exit code beyond the standard
contract table, and it exists so an agent can tell "the tool needs an update" apart from "I'm
being throttled."

## What "drift" actually is

nook talks to Airbnb's own internal `/api/v3` GraphQL — the same API the airbnb.com web app
calls. There is no public, versioned, documented API here, so nook depends on a few things that
Airbnb could change at any time without notice:

- **The public API key.** Airbnb ships a static `X-Airbnb-Api-Key` to every anonymous visitor,
  scraped live off the homepage. nook caches it in `$XDG_STATE_HOME/nook/` and falls back to a
  long-known value (`d306zoyjsyarp7ifhu67rjxn52tv0t20`) if the scrape misses.
- **Persisted-query hashes.** Each GraphQL operation nook actually calls — `StaysSearch`
  (search), `PdpAvailabilityCalendar` (availability), `StaysPdpReviewsQuery` (reviews) — is
  identified by a sha256 hash of its query text. Airbnb has kept most of these stable — except
  `StaysSearch`, which rotates.
- **Response shape.** Field names and nesting inside those GraphQL payloads (and inside the PDP
  page's embedded `data-deferred-state-0` script that `nook listing get` parses directly, with no
  persisted-query hash involved) are Airbnb's internal implementation detail, not a contract.

When any of these shift out from under nook and it can't recover, you get exit `20` instead of a
crash or silently-wrong data.

## How it differs from a rate limit (exit 7)

These two are easy to confuse from the outside — both come from talking to Airbnb — but they mean
opposite things and call for opposite responses:

| | Exit `7` `RATE_LIMITED` | Exit `20` `UPSTREAM_DRIFT` |
|---|---|---|
| Cause | Airbnb blocked/challenged *this client* (403, 429, CAPTCHA) | Airbnb changed its *own internals* (key/hash/shape) |
| What it says about the request | The request was probably fine | The request shape nook sent may now be stale |
| Right response | Back off — nook's circuit breaker is already open; don't retry into it | Update nook — retrying won't help until the tool ships a fix |
| See also | [Rate-limited (exit 7)](/troubleshooting/rate-limited/) | this page |

If you're not sure which one you hit, check the `code` field in the error envelope on stderr:
`RATE_LIMITED` vs `UPSTREAM_DRIFT`. Never treat a `20` as a reason to retry — retrying the same
request against the same broken assumption just repeats the failure.

## The StaysSearch self-heal

`nook search` doesn't give up at the first sign of a stale hash. On every search, nook:

1. Sends the request with the currently-cached `StaysSearch` hash.
2. If Airbnb comes back with a `PersistedQueryNotFound`-style GraphQL error, nook re-scrapes the
   homepage and its JS entry bundles looking for a fresh 64-hex-character hash near a
   `StaysSearch` reference, and retries **once** with that new hash.
3. If the re-scrape can't find a hash, or the freshly-scraped hash is rejected too, nook gives up
   and raises `UPSTREAM_DRIFT` — it does not retry indefinitely or guess.

This self-heal is why a `StaysSearch` hash rotation is usually invisible to you: nook recovers in
the same call. You'll only ever see exit `20` for `StaysSearch` when the self-heal itself fails
(Airbnb reworked the bundle layout, not just the hash value).

The other persisted-query hashes (`PdpAvailabilityCalendar`, `StaysPdpReviewsQuery`) are
known-good constants — nook doesn't attempt to self-heal those. If one of them breaks, and the
expected node (`calendarMonths`, `reviews`) goes missing without a GraphQL error attached, nook
raises `UPSTREAM_DRIFT` directly rather than guess at a reshaped payload. `nook listing get`
doesn't use a persisted-query hash at all — it parses the PDP page's embedded state script
directly, so its drift case is a bit different: if that script is present but its JSON can't be
parsed, nook raises `UPSTREAM_DRIFT`. If the script is missing entirely, nook can't tell a genuine
404/removed listing apart from a page-layout change, so it reports [not
found](/reference/exit-codes/) (exit `5`) rather than drift.

## What it looks like

```bash
nook search "Lisbon" --json
```

```text
{"error":"Airbnb's internal API shape changed: StaysSearch persisted-query hash rotated and re-scrape failed","code":"UPSTREAM_DRIFT","remediation":"update nook to a newer release (uv tool install --upgrade nook); this is not a rate limit"}
```

That JSON goes to **stderr**; the process exits `20`. Other drift messages you might see instead
of the one above:

- `"StaysSearch rejected even the freshly-scraped hash"`
- `"StaysSearch response missing the expected results node"`
- `"PdpAvailabilityCalendar response shape changed"`
- `"reviews response shape changed"`
- `"could not parse the listing page state blob"`

All of them carry the same `code` (`UPSTREAM_DRIFT`), the same exit (`20`), and the same
remediation.

## The fix: update nook

There's no workaround from your side — the fix ships from nook, not from retrying or changing
flags. Check for an update and install it:

```bash
nook version --check
```

```json
{
  "current": "0.3.1",
  "latest": "0.4.0",
  "updateAvailable": true,
  "upgrade": "uv tool install --upgrade nook"
}
```

(`doctor`, `schema`, `agent`, and `version` are diagnostic/meta commands — their output isn't
wrapped in the read envelope described in [Output envelope](/concepts/output-envelope/); that
envelope applies to `search`/`listing get`/`availability`/`reviews`/`place search`.)

nook never self-updates — `version --check` only reports the update command; you run it:

```bash
uv tool install --upgrade nook
# or, for a one-off invocation:
uvx nook@latest search "Lisbon" --json
```

If `nook version --check` shows you're already on the latest release and you're still hitting
`UPSTREAM_DRIFT`, the fix hasn't shipped yet — Airbnb moved faster than the release. `nook doctor`
is a useful first stop to confirm this isn't actually a transport or breaker issue:

```bash
nook doctor --json
```

```json
{
  "ok": true,
  "checks": [
    {"name": "transport", "ok": true, "detail": "curl_cffi present (Chrome TLS impersonation available)"},
    {"name": "circuit_breaker", "ok": true, "detail": "closed"},
    {"name": "key_cache", "ok": true, "detail": "cached"},
    {"name": "auth", "ok": true, "detail": "no auth required (public logged-out access)"}
  ],
  "legitimacy": "reads public logged-out data at personal scale; no evasion (no proxies/CAPTCHA); circuit-breaks on a block. See `nook agent`."
}
```

If the breaker is closed and transport is healthy but you're still getting exit `20`, this is a
genuine upstream break — Airbnb changed something nook doesn't yet know how to handle. There's
nothing to configure around it; wait for a release, or open an issue with the exact `error`
message and the command you ran.

## Related

- [Rate-limited (exit 7)](/troubleshooting/rate-limited/) — the other Airbnb-facing failure mode, and how it differs from drift.
- [Exit codes](/reference/exit-codes/) — the full exit-code table.
- [Backend etiquette](/concepts/etiquette/) — why nook self-throttles and circuit-breaks instead of retrying through either failure.
