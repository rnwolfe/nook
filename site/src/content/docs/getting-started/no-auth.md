---
title: No auth
description: nook never logs in — it reads public, logged-out Airbnb pages, and every read says so in its scope.
---

There are no credentials to configure, no login flow to script, and no API key for you to obtain.
`nook` reads only the pages Airbnb serves to an anonymous, logged-out visitor — the same view you'd
get browsing incognito. Nothing in the setup asks for a username, password, cookie, or session token.

## Why there's nothing to configure

Airbnb's own web app authenticates its internal `/api/v3` GraphQL endpoint with a **public static
API key** it ships to every anonymous visitor in the page HTML. `nook` reads that same key off the
homepage — it's not a secret, and it's not *your* secret. There's no per-user credential to issue,
so there's nothing for you to sign up for, paste into an env var, or leak.

That also means "no auth" is a hard boundary, not just an implementation shortcut: `nook` cannot see
anything a logged-out browser can't. No saved trips, no host inbox, no private listings, no
account-gated pricing. If a page requires being signed in, `nook` doesn't fetch it — see
[Read-only](/concepts/read-only/) and [Legitimacy](/concepts/legitimacy/) for the full boundary and
why that's not just a technical limitation but a deliberate one.

## The scope envelope

Because "public, logged-out" is a real constraint on completeness (not every listing's full detail
is visible to an anonymous visitor, and prices/availability can differ from what a signed-in guest
sees), every read command says so explicitly. Every successful envelope carries a fixed `scope`
object:

```json
{
  "schemaVersion": 1,
  "scope": { "auth": "none", "corpus": "public-logged-out" },
  "data": { "...": "..." },
  "nextCursor": null,
  "meta": { "count": 12, "truncated": false }
}
```

`scope.auth` is always `"none"` — there is no other value; `nook` never authenticates.
`scope.corpus` is always `"public-logged-out"` — a standing reminder to whatever's consuming the
output (you, or an agent) that this is the anonymous view, not a complete or account-aware one. It's
the same two fields on `search`, `place search`, `listing get`, `availability`, and `reviews` — see
[The output envelope](/concepts/output-envelope/) for the rest of the shape.

You can also see the same fact reported by `nook doctor`, which checks connectivity and reports:

```bash
nook doctor
```

```json
{
  "ok": true,
  "checks": [
    { "name": "transport", "ok": true, "detail": "curl_cffi present (Chrome TLS impersonation available)" },
    { "name": "circuit_breaker", "ok": true, "detail": "closed" },
    { "name": "key_cache", "ok": true, "detail": "cached" },
    { "name": "auth", "ok": true, "detail": "no auth required (public logged-out access)" }
  ],
  "legitimacy": "reads public logged-out data at personal scale; no evasion (no proxies/CAPTCHA); circuit-breaks on a block. See `nook agent`."
}
```

## What's in $XDG_STATE_HOME/nook

`nook` still needs a little bit of state between calls — but it's never yours. Because an agent
invokes `nook` as a **fresh process every time**, anything that needs to persist across calls (a
throttle timer, a circuit-breaker window, a scraped cache) has to live on disk, not in memory. That
state lives under `$XDG_STATE_HOME/nook/` (defaulting to `~/.local/state/nook/` if
`XDG_STATE_HOME` isn't set; the directory is created with `0700` permissions). It holds three small
JSON files:

- **`keyhash.json`** — the live-scraped public `X-Airbnb-Api-Key` (with a TTL) and, when
  self-healing kicks in, a re-scraped `StaysSearch` persisted-query hash. Both are values Airbnb
  ships to every anonymous browser — caching them just avoids re-scraping the homepage on every
  call. If the scrape ever misses, `nook` falls back to a long-known public key value rather than
  failing outright.
- **`throttle.json`** — the timestamp of the last upstream request, so cross-process calls honor a
  minimum ~1 request/second spacing (jittered) instead of one process resetting the clock every
  time.
- **`breaker.json`** — the circuit-breaker window: if Airbnb responds with a block or challenge
  (403/429/CAPTCHA), `nook` trips this for a cooldown (15 minutes by default, or whatever
  `Retry-After` said) so it fails fast instead of hammering a block. `nook doctor` reports this as
  `circuit_breaker`.

None of these files contain anything specific to you — no session, no cookie, no personal
identifier. They exist purely so `nook` behaves like a polite, rate-aware guest across many
short-lived invocations. Deleting the directory is always safe: the next call just re-scrapes the
key and starts throttling fresh. See [Etiquette](/concepts/etiquette/) for why the throttle and
breaker exist, and [Rate limited](/troubleshooting/rate-limited/) for what to do if the breaker
trips.

## What this means day to day

- `nook doctor`, `nook search`, `nook availability`, and every other command work the moment you
  install `nook` — see [Install](/getting-started/install/) and
  [Quickstart](/getting-started/quickstart/). There's no "log in first" step.
- You'll never be prompted for a token, and there's no `NOOK_API_KEY` or similar to set.
- `nook schema | jq .scope` and `nook schema | jq .readOnly` both reflect this at a glance — useful
  for an agent deciding whether it's safe to call `nook` without any credential wiring.
- Because the corpus is logged-out, expect the occasional gap versus what you'd see signed in
  (some listings render less detail, some pricing nuances are account-specific). `nook` never hides
  this — it's baked into every `scope` field you get back.
