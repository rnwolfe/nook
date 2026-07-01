---
title: Checking availability
description: The wedge — a free forward availability calendar with per-day available, min-nights, and price.
---

`nook availability <id>` answers the one question search and listing details can't: **which
specific dates are actually open, right now, for this listing** — and at what price. It's a
forward, per-day calendar, and it's the piece of this tool that doesn't exist anywhere else for
free.

```bash
nook availability 12345678 --months 2 --json
```

## Why this command exists

Search returns listings that match a date range you already picked. Listing details returns the
static shape of a place — bedrooms, amenities, host. Neither tells you, for a listing you're
already interested in, *which upcoming nights are bookable* so an agent can compare options or
build a trip around real open dates.

Free tooling doesn't cover this gap. The maintained MCP server for Airbnb search does listing
search and details with no calendar. The other agent-facing Airbnb CLI in the wild does search and
get, also with no forward-availability dump. The only other place a calendar like this exists is a
paid, closed scraping actor. `nook availability` is the first free, local, agent-grade forward
calendar for Airbnb listings — that's why the spec calls it **the wedge**.

## Two ways to pick the window

`--months` is the simple path: an integer from 1 to 12 (default 1), counted forward from today.

```bash
nook availability 12345678 --months 3 --json
```

`--start`/`--end` (both `YYYY-MM-DD`) let you pin an exact date range instead:

```bash
nook availability 12345678 --start 2026-08-01 --end 2026-08-31 --json
```

Both flags exist because of how the upstream calendar actually works: Airbnb serves the calendar
in whole months (up to 12 forward from the current month), and `nook` fetches enough whole months
to cover whatever window you asked for, then filters the per-day list down to your exact range
client-side. Concretely:

- With only `--months N`, the window is `[today, today + N months]`.
- With `--start`/`--end`, they **override** the months-based window — `--start` defaults to today
  if omitted, `--end` defaults to `today + months` if omitted. Days outside `[start, end]` are
  dropped before the envelope is built.
- `--months` still controls how many calendar months are fetched from Airbnb under the hood (it's
  clamped to 1–12), so if you pass a `--start`/`--end` range that reaches further out than 1 month,
  raise `--months` too or you'll get a truncated calendar back.

```bash
# Same effect, two ways: next ~2 months, filtered to just the last two weeks of that window
nook availability 12345678 --months 2 --start 2026-08-15 --end 2026-08-31 --json
```

## The per-day shape

Every item in `data` is one calendar day:

```json
{
  "date": "2026-08-14",
  "available": true,
  "availableForCheckin": true,
  "availableForCheckout": false,
  "bookable": true,
  "minNights": 2,
  "maxNights": 28,
  "price": { "amount": 214, "currency": "USD" }
}
```

Field notes:

- **`date`** — `YYYY-MM-DD`, the calendar day.
- **`available`** — whether the night is open at all.
- **`availableForCheckin`** / **`availableForCheckout`** — Airbnb tracks these separately from
  plain `available` because a night can be blocked as a checkin (e.g. it falls inside another
  guest's stay) while still being valid as a checkout, or vice versa. Don't collapse these into
  one boolean — an agent building a trip needs to know which end of a stay a date can anchor.
- **`bookable`** — the host/backend's overall bookability signal for that day (can differ from
  `available` due to minimum-stay rules, host settings, etc.).
- **`minNights`** / **`maxNights`** — the stay-length constraints in effect for a stay starting
  that day.
- **`price`** — `{amount, currency}` for that night, or `null` if Airbnb didn't return a parseable
  price for the day (this happens; don't assume every day has one). Prices come back as
  formatted strings from Airbnb (e.g. `"$214"`) and `nook` parses them into `{amount, currency}` —
  if the format is unrecognized, `price` is `null` rather than a guess.

There is no `nights`/aggregate object — this is a flat list of days, one per date in the resolved
window, in calendar order.

## Currency

```bash
nook availability 12345678 --months 1 --currency EUR --json
```

`--currency` is an ISO code (`USD`, `EUR`, `GBP`, ...) applied to the upstream request; it defaults
to `USD` if omitted. It shows up twice: as the `currency` field inside each day's `price` object,
and as `meta.currency` in the envelope, so an agent can read a single value once instead of
scanning every row.

## How it rides the envelope

Like every read in nook, `availability` returns the standard envelope — see
[Output envelope](/concepts/output-envelope/) for the full shape. For availability specifically:

```json
{
  "schemaVersion": 1,
  "scope": { "auth": "none", "corpus": "public-logged-out" },
  "data": [
    { "date": "2026-08-01", "available": true, "availableForCheckin": true,
      "availableForCheckout": true, "bookable": true, "minNights": 2, "maxNights": 28,
      "price": { "amount": 189, "currency": "USD" } }
  ],
  "nextCursor": null,
  "meta": { "count": 31, "truncated": false, "total": 31, "currency": "USD" }
}
```

A few things worth calling out:

- **`nextCursor` is always `null` here.** Availability isn't cursor-paginated — you already bound
  the result set with `--months`/`--start`/`--end`. If you need a wider window, ask for it with a
  bigger window on the next call, not a cursor.
- **`--limit` still applies** (default 50) since `data` is a list. A single month is ~30 days, so
  this rarely bites — but if you ask for 12 months (~365 days) with the default limit, you will get
  `meta.truncated: true` and a `note:` on stderr telling you it was cut to 50. Raise `--limit` to
  see the whole range in one call.
- **`--select`** projects fields per day if you only care about a subset, e.g.
  `--select date,available,price` to drop the checkin/checkout/bookable detail.
- **`meta.currency`** mirrors the resolved currency (your `--currency`, or `USD` default) so you
  don't have to re-derive it from the first row.

## Exit codes specific to this command

- **`0`** — calendar returned (even if every day shows `available: false`; that's data, not an
  error).
- **`5`** (`not_found`) — the listing id is invalid, private, or removed. `nook` distinguishes a
  genuine "no calendar" response from a reshaped upstream response: if Airbnb's shape changes in a
  way `nook` doesn't recognize, you'll get `20` instead (see below), not a silent empty result.
- **`7`** (`rate_limited`) — Airbnb's circuit breaker tripped (403 challenge / 429 / CAPTCHA). Don't
  retry into it — see [Rate limited](/troubleshooting/rate-limited/). Pass `--wait` to block until
  the breaker clears instead of failing fast.
- **`20`** (`UPSTREAM_DRIFT`) — Airbnb reshaped the `PdpAvailabilityCalendar` response. This is
  distinct from a block: it means the tool likely needs an update. See
  [Upstream drift](/troubleshooting/upstream-drift/).

Full table: [Exit codes](/reference/exit-codes/).

## Putting it together

Resolve a location, search with dates as a first filter, then use `availability` to see the wider
picture around a specific listing you like:

```bash
nook place search "Asheville, NC" --json
nook search "Asheville, NC" --checkin 2026-09-10 --checkout 2026-09-14 --guests 2 --json
nook availability 987654321 --months 3 --currency USD --json
```

The third call is the one that lets an agent answer "is there a 4-night window in the next 90 days
that this listing is actually free for, and at what price" — without booking anything, and without
needing a login. See also [Searching](/guides/searching/) and
[Listing details](/guides/listing-details/) for the surrounding two commands, and
[Read-only](/concepts/read-only/) for why there is no booking path at all.
