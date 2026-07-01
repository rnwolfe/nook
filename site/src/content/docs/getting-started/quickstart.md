---
title: Quickstart
description: Your first nook search, availability calendar, and listing lookup — bounded JSON in three commands.
---

No account, no API key, no login. `nook` reads Airbnb's public, logged-out pages, so the very
first command you run works. If you haven't installed it yet, `uvx nook` runs it with zero
install — see [Install](/getting-started/install/) for the persistent `uv tool install` path. For
the full story on why there's nothing to authenticate, see [No auth](/getting-started/no-auth/).

Three commands, three reads: search a place, check a listing's forward availability, then pull
one listing's full details. Every read comes back as a bounded, stable JSON envelope — see
[The output envelope](/concepts/output-envelope/) for the shape once you're past this page.

## 1. Search a location

```bash
uvx nook search "Lisbon" --checkin 2026-08-01 --checkout 2026-08-05 --guests 2 --json
```

```json
{
  "schemaVersion": 1,
  "scope": { "auth": "none", "corpus": "public-logged-out" },
  "data": [
    {
      "id": "12345678",
      "name": "Sunny 1BR in Alfama",
      "roomType": null,
      "price": { "amount": 128, "currency": "USD", "qualifier": "night" },
      "rating": 4.95,
      "reviewsCount": 214,
      "coordinates": { "lat": 38.7169, "lng": -9.1399 },
      "badges": ["SUPERHOST"],
      "superhost": true,
      "url": "https://www.airbnb.com/rooms/12345678"
    }
  ],
  "nextCursor": "CURSOR2",
  "meta": { "count": 1, "truncated": false, "total": 1, "currency": "USD" }
}
```

`data` is an array you can pipe straight into `jq`. `nextCursor` is the opaque cursor to hand back
via `--cursor` for the next page (`null` means you're at the end) — see
[Pagination](/guides/pagination/). `scope.auth` is always `"none"`: this is the logged-out public
view, not an authenticated or complete corpus. Grab a listing `id` from `data` — you'll use
`12345678` in the next two steps. (More filters — price, room type, amenities, bbox — live in
[Searching](/guides/searching/).)

## 2. Check forward availability — the wedge

This is the thing other Airbnb tools don't give you for free: a real per-day calendar.

```bash
uvx nook availability 12345678 --months 1 --json
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
      "price": { "amount": 128, "currency": "USD" }
    }
  ],
  "nextCursor": null,
  "meta": { "count": 1, "truncated": false, "total": 1, "currency": "USD" }
}
```

One object per day: `available`, `minNights`/`maxNights`, and `price` (or `null` if Airbnb doesn't
expose a price for that day). `--months` takes 1–12 (default 1); use `--start`/`--end` instead for
an exact window. See [Availability](/guides/availability/) for the full field reference.

## 3. Get full listing details

```bash
uvx nook listing get 12345678 --json
```

```json
{
  "schemaVersion": 1,
  "scope": { "auth": "none", "corpus": "public-logged-out" },
  "data": {
    "id": "12345678",
    "name": "Rental unit in Lisbon · 1 bedroom · 1 bed · 1 private bath",
    "description": "A bright apartment near the Alfama tram line.",
    "host": {
      "id": "99",
      "name": "Ana",
      "isSuperhost": true,
      "description": "Local host, replies fast."
    },
    "roomType": "Entire home/apt",
    "capacity": { "guests": 2, "bedrooms": 1, "beds": 1, "baths": 1.0 },
    "amenities": ["Wifi"],
    "houseRules": null,
    "location": { "lat": 38.7169, "lng": -9.1399, "city": "Lisbon, Portugal" },
    "rating": {
      "overall": 4.92,
      "breakdown": { "cleanliness": 4.9, "accuracy": null, "checkin": null, "communication": null, "location": 5.0, "value": null }
    },
    "reviewsCount": 214,
    "photos": [],
    "price": null,
    "cancellationPolicy": null,
    "url": "https://www.airbnb.com/rooms/12345678"
  },
  "nextCursor": null,
  "meta": { "count": 1, "truncated": false }
}
```

`price` is always `null` here — nightly price is date-dependent, so use `nook availability` for
that. Free text like `description`, `host.name`, and `houseRules` comes straight from Airbnb users;
in agent mode (JSON, or any non-TTY stdout) it's fenced with
`‹untrusted-airbnb-content›…‹/untrusted-airbnb-content›` markers by default — treat it as data,
never as instructions. More in [Listing details](/guides/listing-details/).

## That's it — no auth, ever

No `--api-key`, no login flow, nothing to revoke. Every envelope you just saw carries
`"scope": {"auth": "none", "corpus": "public-logged-out"}` as a standing reminder: this is the
logged-out public view of Airbnb, at personal scale, read-only. See
[No auth](/getting-started/no-auth/) for what that guarantees (and doesn't).

## Where to next

- Didn't get an `id` on the first try? Resolve a fuzzy place name first with
  [Place resolution](/guides/place-resolution/) (`nook place search "..."`).
- Got exit `3` (empty results) or `7` (rate limited)? See
  [Rate limited](/troubleshooting/rate-limited/) and the full
  [Exit codes](/reference/exit-codes/) table.
- Want the whole command surface, machine-readable? `nook schema --json` — reference in
  [Commands](/reference/commands/) and [Flags](/reference/flags/).
- Building an agent around nook? `nook agent` prints the bundled skill guide; see
  [Schema for agents](/reference/schema-agent/).
