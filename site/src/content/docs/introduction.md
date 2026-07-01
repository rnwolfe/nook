---
title: Introduction
description: nook is a read-only, JSON-first Airbnb search and forward-availability CLI for AI agents — booking excluded by design, no auth, no evasion.
---

nook gives an AI agent (or you) clean, bounded JSON for Airbnb **listing search/discovery**,
**listing details**, and a **forward availability calendar** — per-day `available`,
`availableForCheckin`, `availableForCheckout`, `bookable`, `minNights`, `maxNights`, and `price`.
That calendar is the piece other Airbnb tools don't hand you for free, and it's the reason nook
exists.

It never books, never logs in, and reads only public, logged-out data.

## The wedge: a forward availability calendar

Most Airbnb scrapers stop at search results — a list of listings with a headline price. That's
useful, but it doesn't answer the question an agent actually needs answered: **is this place free
on the dates I care about, and what does the price curve look like around them?**

`nook availability <id>` answers that directly. Point it at a listing ID and a window
(`--months 1..12`, or an explicit `--start`/`--end`), and it returns a day-by-day calendar:

```bash
nook availability 12345678 --months 3 --limit 100 --json
```

```json
{
  "schemaVersion": 1,
  "scope": { "auth": "none", "corpus": "public-logged-out" },
  "data": [
    {
      "date": "2026-08-01",
      "available": true,
      "availableForCheckin": true,
      "availableForCheckout": false,
      "bookable": true,
      "minNights": 2,
      "maxNights": 28,
      "price": { "amount": 142, "currency": "USD" }
    }
  ],
  "nextCursor": null,
  "meta": { "count": 90, "truncated": false, "total": 90 }
}
```

(`--limit 100` here raises the default cap of 50 items so a full 90-day, 3-month calendar comes
back in one page instead of a truncated one.) That's a calendar an agent can reason over
directly — no scraping the search UI over and over to triangulate open dates, no guessing at
minimum-stay rules. See [Availability](/guides/availability/) for the full shape and how the
flags interact.

## Who it's for

nook is built for AI agents driving a shell — coding agents, research agents, travel-planning
agents — that need structured Airbnb data as part of a larger task, plus the humans who script
alongside them. It's JSON-first: every read returns a stable, bounded envelope
(see [The output envelope](/concepts/output-envelope/)) instead of scraped HTML or a wall of
prose. If you're piping output into `jq`, feeding it to another tool, or having an LLM read it
straight off stdout, this is the shape you want.

## Read-only, no auth, booking excluded — on purpose

Three constraints shape everything about how nook works, and they're all deliberate:

- **Read-only.** No nook command mutates anything on Airbnb. The contract flags
  `--allow-mutations`, `--dry-run`, `--yes`, and `--force` exist only for uniformity with other
  agent CLIs that *do* have mutating commands — in nook they're inert no-ops. See
  [Read-only by design](/concepts/read-only/).
- **No auth.** nook never asks for an API key, a login, or any secret. It reads the same
  logged-out public pages a browser sees before you sign in. Every read envelope carries
  `"scope": {"auth": "none", "corpus": "public-logged-out"}` as a standing reminder that this is
  the public view, not an authenticated or complete corpus. See
  [No auth, no setup](/getting-started/no-auth/).
- **Booking excluded by design.** There is no `nook book` command, and there never will be —
  transacting on Airbnb is out of scope for this tool, full stop.

nook is also careful about *how* it reads: it self-throttles across processes, circuit-breaks
the moment Airbnb pushes back (a block, a rate limit, a CAPTCHA challenge) instead of retrying
into it, and never disguises its identity with proxies or IP rotation. It presents the same
TLS/client fingerprint and the same public API key a real logged-out browser session would.
See [Legitimacy](/concepts/legitimacy/) and [Etiquette](/concepts/etiquette/) for the full
reasoning and the case law behind it.

## Conformance

nook conforms to the [Agent CLI Guidelines](https://aclig.dev) at **v0.4.0**, level **Full**.
You can verify this yourself once it's installed:

```bash
nook schema | jq .conformance
```

## Get started

- [Install nook](/getting-started/install/) — `uvx nook` for a zero-install trial, or
  `uv tool install nook` for repeated / agent-loop use.
- [Quickstart](/getting-started/quickstart/) — your first search, listing, and availability call.
- [Availability](/guides/availability/) — the full calendar shape, the wedge in depth.
