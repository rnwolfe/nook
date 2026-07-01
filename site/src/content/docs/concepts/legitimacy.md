---
title: Safety & the legitimacy boundary
description: nook reads public, logged-out pages at personal scale — and if blocked, it stops rather than evades.
---

`nook` is unofficial. There is no Airbnb partnership, no sanctioned API, no blessing. It works by
reading the same public, logged-out pages a browser would load, at the pace a single person
planning a trip would generate. This page is the honest accounting of what that means, what the
risk actually is, and where the line sits — so you (or the agent running `nook` on your behalf)
can make an informed call instead of an uninformed one.

If you read nothing else: **`nook` reads publicly visible, logged-out Airbnb pages at personal,
single-user scale, read-only. If Airbnb blocks it, the correct response is to stop, not to
evade. This is not legal advice.**

## What "public, logged-out, personal scale" means

Three qualifiers, and all three matter:

- **Public** — everything `nook` reads is visible to anyone with a browser and no account:
  search results, listing pages, availability calendars, reviews. Nothing behind a login wall,
  nothing account-specific, nothing paywalled.
- **Logged-out** — `nook` never authenticates. There's no `nook login`, no API key you supply, no
  session cookie, no credential of any kind. See [No auth, no login](/getting-started/no-auth/)
  for what that means mechanically.
- **Personal, single-user scale** — a handful of queries for your own trip planning, at
  human-like pacing, self-throttled and circuit-broken (see
  [Backend etiquette & the circuit-breaker](/concepts/etiquette/)). Not a crawl, not a dataset
  build, not a scrape-and-resell operation.

That combination — public data, no auth, one person's worth of traffic — is deliberately the
lowest-risk shape automated access to a site can take. It's also the shape this page's legal
framing below actually applies to. Log in, scale up, or start scraping to resell, and none of the
reasoning here transfers.

## The contract you're accepting

Airbnb's Terms of Service prohibit automated access outright: *"Do not use bots, crawlers,
scrapers, or other automated means to access or collect data … from … the Airbnb Platform."*
`robots.txt` disallows the `/s/*/*` search paths and specifically asks AI-named agents off
`/rooms/` entirely.

`nook` doesn't pretend otherwise, and it doesn't try to get around either of those. Using `nook`
means you're choosing to act against Airbnb's stated terms and its `robots.txt` preference. That's
real, and it's yours to weigh — not something the tool hides from you or downplays.

## Why that's a contract term, not a crime

The distinction that matters here: a website's Terms of Service is a **contract**, and a contract
you never agreed to (because you never logged in, never clicked "I agree") generally doesn't bind
you the way criminal statutes do. Three U.S. cases shape this reading:

- ***Van Buren v. United States*** (2021) — the Supreme Court narrowed the Computer Fraud and
  Abuse Act so that violating a website's *use policy* isn't, by itself, "exceeding authorized
  access" in the criminal sense.
- ***hiQ Labs v. LinkedIn*** (9th Cir. 2022) — accessing publicly available web pages doesn't
  violate the CFAA, even against the site owner's wishes. (hiQ ultimately still lost the broader
  case — to LinkedIn, on other contract-law grounds — which is exactly the point below.)
- ***Meta Platforms v. Bright Data*** (N.D. Cal. 2024) — a court held that Meta's Terms of
  Service bind only *logged-in* users; logged-out, public access isn't a party to that contract at
  all.

Put together: for public, logged-out data, accessing it against a ToS is generally not a
**computer crime** in the U.S. It can still be a **contract** problem — Airbnb can rate-limit you,
block you, or (in principle) pursue a breach-of-contract claim or cease-and-desist, the way
LinkedIn ultimately prevailed against hiQ on contract grounds even after hiQ won the CFAA argument.
`nook` sits deliberately at the low-risk end of that spectrum — public, logged-out, personal scale
— but "low-risk" is not "zero-risk," and none of this is a promise that Airbnb can't or won't act.

## What "no evasion" means in practice

`nook`'s only lever here is honesty about volume, never disguise of identity. Concretely:

- HTTP goes out via `curl_cffi` with `impersonate="chrome"` — matching a real Chrome client's
  TLS/JA3 fingerprint — and Airbnb's own **public** static API key, scraped from the homepage the
  same way a browser's JS bundle would load it. That's presenting the real client's fingerprint
  honestly, not spoofing a fake one.
- No proxies. No IP rotation. No CAPTCHA solving. No residential-proxy networks.
- A cross-process self-throttle (roughly one request per second, jittered) and a persisted
  circuit-breaker that trips on a block and stays tripped — see
  [Backend etiquette & the circuit-breaker](/concepts/etiquette/).

If Airbnb tightens up and starts blocking `nook` more aggressively, the answer is fewer, slower
requests — never a workaround. `nook` makes that structurally true: when Airbnb returns a 403
challenge, a 429, or a CAPTCHA ("Press & Hold"), `nook` trips its breaker and exits `7`
(`RATE_LIMITED`) rather than retrying past it. See
[Troubleshooting: rate limited](/troubleshooting/rate-limited/) for what to do when you hit that.

## If Airbnb blocks nook, stop

This is the core operating rule, and it's not negotiable: **if Airbnb blocks `nook`, stop. Don't
evade it.** Don't reach for a proxy. Don't rotate IPs. Don't script around the circuit-breaker.
Back off, and if you need `nook` to keep working over time, use `--wait` to block until the
throttle window clears on its own rather than fighting it. A block is Airbnb telling you the
current pace or pattern isn't acceptable to them — `nook`'s job is to hear that and comply, not to
find a quieter way to keep doing the same thing.

The same posture applies if Airbnb changes its internal API shape out from under `nook` — that's
a different signal (`20`, `UPSTREAM_DRIFT`, meaning the tool itself needs an update), not a block,
and is covered in [Troubleshooting: upstream drift](/troubleshooting/upstream-drift/).

## What this is not

This page — and everything `nook` tells you about legitimacy — is **not legal advice**. It's an
honest account of the reasoning `nook` was built on, with real citations you can go check yourself.
If you're building something at real scale, operating commercially, or just want certainty instead
of a reasoned bet, talk to a lawyer. `nook` is scoped, deliberately, to stay well inside the
"personal, single-user, public, logged-out" shape where this reasoning holds — stray outside that
shape and you're on your own.

## See also

- [Read-only & booking-excluded](/concepts/read-only/) — the other half of nook's safety posture.
- [Backend etiquette & the circuit-breaker](/concepts/etiquette/) — how the self-throttle and
  circuit-breaker work mechanically.
- [No auth, no login](/getting-started/no-auth/) — why there's nothing to log in with in the
  first place.
- [Troubleshooting: rate limited](/troubleshooting/rate-limited/) — what exit `7` means and what
  to do about it.
- [Exit codes](/reference/exit-codes/) — the full table, including `7` and `20`.
