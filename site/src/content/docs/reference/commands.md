---
title: Commands
description: The full nook command surface — search, place search, listing get, availability, reviews, doctor, schema, agent, version.
---

Every nook command is **read-only**. Nothing here books, cancels, messages a host, or changes any
state on Airbnb — there is nothing to "undo." The mutation-gate flags (`--allow-mutations`,
`--dry-run`, `--yes`, `--force`) exist purely for contract uniformity with other agent CLIs; nook
never calls the gate, so they're inert no-ops on every command below.

All commands accept the [global flags](/reference/flags/) (`--format`, `--json`, `--limit`,
`--select`, `--no-wrap`, …). Commands that hit the network also accept `--wait` / `--max-wait`.
Reads return the [output envelope](/concepts/output-envelope/); errors go to stderr and map to
one of the [exit codes](/reference/exit-codes/).

## Command table

| Command | Args | Purpose | Read/mutation | Example |
|---|---|---|---|---|
| `nook search <location>` | `location` + filters | Search listings in a place | read | `nook search "Lisbon" --json` |
| `nook place search <query>` | `query` | Resolve a location string to a precise place | read | `nook place search "Lisbon" --json` |
| `nook listing get <id>` | `listing_id` | Full details for one listing | read | `nook listing get 12345678 --json` |
| `nook availability <id>` | `listing_id` + window | Forward per-day calendar | read | `nook availability 12345678 --months 3 --json` |
| `nook reviews <id>` | `listing_id` | Recent reviews for a listing | read | `nook reviews 12345678 --json` |
| `nook doctor` | — | Diagnose connectivity/transport/breaker state | read | `nook doctor --json` |
| `nook schema` | — | Machine-readable command schema | read | `nook schema --json` |
| `nook agent` | — | Print the bundled agent guide (`SKILL.md`) | read | `nook agent` |
| `nook version [--check]` | — | Print version, or check for an update | read | `nook version --check --json` |

---

## `nook search`

```text
nook search <location> [FILTERS]
```

Search Airbnb listings in a location — the marquee discovery command. `<location>` is a bare
string; it becomes the query unless `--bbox` or `--place-id` is given, which switch to a map
(bounding-box) or resolved-place search instead.

**Filters:**

| Flag | Type | Notes |
|---|---|---|
| `--checkin` / `--checkout` | date `YYYY-MM-DD` | Stay window |
| `--guests` | int | Total guests |
| `--adults` / `--children` / `--infants` / `--pets` | int | Guest breakdown |
| `--min-price` / `--max-price` | int | Nightly price bounds |
| `--room-type` | `entire\|private\|shared\|hotel` | Room type filter |
| `--bedrooms` / `--beds` / `--bathrooms` | int | Minimums |
| `--amenities` | comma list | e.g. `--amenities wifi,pool` |
| `--superhost` | flag | Superhost listings only |
| `--place-id` | string | A resolved place id, from `nook place search` |
| `--bbox` | `"neLat,neLng,swLat,swLng"` | Bounding-box (map) search |
| `--currency` | ISO code | e.g. `USD` |
| `--cursor` | opaque string | Page forward from a prior `nextCursor` |

Plus [net flags](/reference/flags/) (`--wait`, `--max-wait`) and all global flags.

```bash
nook search "Lisbon" --checkin 2026-08-01 --checkout 2026-08-05 --guests 2 \
  --room-type entire --min-price 80 --max-price 250 --json
```

```json
{
  "schemaVersion": 1,
  "scope": { "auth": "none", "corpus": "public-logged-out" },
  "data": [
    {
      "id": "12345678",
      "name": "‹untrusted-airbnb-content› Sunny flat near Alfama ‹/untrusted-airbnb-content›",
      "roomType": null,
      "price": { "amount": 145, "currency": "USD", "qualifier": "for 5 nights" },
      "rating": 4.92,
      "reviewsCount": 128,
      "coordinates": { "lat": 38.7107, "lng": -9.1442 },
      "badges": [],
      "superhost": false,
      "url": "https://www.airbnb.com/rooms/12345678"
    }
  ],
  "nextCursor": "eyJvZmZzZXQiOjUwfQ==",
  "meta": { "count": 1, "truncated": false, "currency": "USD" }
}
```

`roomType` comes back `null` for most search results in practice — Airbnb's search response doesn't
reliably populate it the way the PDP does; treat it as best-effort. For date/price/room-type
strategy and cursor mechanics, see
[Searching](/guides/searching/) and [Pagination](/guides/pagination/). Free-text fields like
`name` are fenced untrusted in agent mode — see [the etiquette guide](/concepts/etiquette/).

Exit codes of note: `7` (rate limited), `8` (retryable upstream error, including a transient
GraphQL error). An empty result set does **not** exit `3` today — it's exit `0` with an empty
`data` array and `meta.count: 0`; see [Exit codes](/reference/exit-codes/#the-full-table).

---

## `nook place search`

```text
nook place search <query>
```

Resolves a fuzzy location string (autocomplete) to concrete place candidates — `placeId`,
coordinates, and a bounding box — so a follow-up `nook search --place-id …` (or `--bbox`) is
deterministic instead of re-guessing the same free-text query. See
[Place resolution](/guides/place-resolution/).

```bash
nook place search "Lisbon" --json
```

```json
{
  "schemaVersion": 1,
  "scope": { "auth": "none", "corpus": "public-logged-out" },
  "data": [
    {
      "placeId": "ChIJ...",
      "name": "Lisbon, Portugal",
      "coordinates": { "lat": 38.7223, "lng": -9.1393 },
      "bbox": { "neLat": 38.8, "neLng": -9.08, "swLat": 38.69, "swLng": -9.23 }
    }
  ],
  "nextCursor": null,
  "meta": { "count": 1, "truncated": false }
}
```

Accepts net flags (`--wait`, `--max-wait`) and global flags. No `--cursor` — this is a small,
single-shot lookup.

---

## `nook listing get`

```text
nook listing get <listing_id>
```

Full details for one listing by id: name, description, host info, house rules, amenities,
location, and pricing metadata, pulled from the listing's embedded page state. Not paginated —
one listing, one object.

```bash
nook listing get 12345678 --json
```

```json
{
  "schemaVersion": 1,
  "scope": { "auth": "none", "corpus": "public-logged-out" },
  "data": {
    "id": "12345678",
    "name": "‹untrusted-airbnb-content› Sunny flat near Alfama ‹/untrusted-airbnb-content›",
    "description": "‹untrusted-airbnb-content› Charming 1BR steps from the tram... ‹/untrusted-airbnb-content›",
    "host": { "name": "‹untrusted-airbnb-content› Ana ‹/untrusted-airbnb-content›", "description": "‹untrusted-airbnb-content› ... ‹/untrusted-airbnb-content›" },
    "houseRules": "‹untrusted-airbnb-content› No smoking. Quiet after 10pm. ‹/untrusted-airbnb-content›",
    "amenities": ["wifi", "kitchen", "washer"]
  },
  "nextCursor": null,
  "meta": { "count": 1, "truncated": false }
}
```

`name`, `description`, `houseRules`, `host.name`, and `host.description` are fenced untrusted in
agent mode by default (contract §8) — see [Reviews](/guides/reviews/) and
[Etiquette](/concepts/etiquette/) for why. If the id is invalid, private, or removed, this exits
`5` (`NOT_FOUND`) rather than returning an empty payload — see [Listing details](/guides/listing-details/).

---

## `nook availability`

```text
nook availability <listing_id> [--months 1..12 | --start --end] [--currency]
```

**This is the wedge** — the thing other Airbnb scrapers don't give you for free: a forward,
per-day calendar for one listing.

| Flag | Type | Notes |
|---|---|---|
| `--months` | int, 1–12, default `1` | Forward window size, in months |
| `--start` / `--end` | date `YYYY-MM-DD` | Overrides the `--months` window; use both together |
| `--currency` | ISO code | Prices in this currency |

Each day in `data` carries:

```text
date, available, availableForCheckin, availableForCheckout, bookable, minNights, maxNights,
price ({amount, currency} | null)
```

```bash
nook availability 12345678 --months 3 --currency USD --json
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
      "maxNights": 30,
      "price": { "amount": 145, "currency": "USD" }
    },
    {
      "date": "2026-08-02",
      "available": false,
      "availableForCheckin": false,
      "availableForCheckout": true,
      "bookable": false,
      "minNights": 2,
      "maxNights": 30,
      "price": null
    }
  ],
  "nextCursor": null,
  "meta": { "count": 2, "truncated": false, "currency": "USD" }
}
```

If the listing id is invalid, private, or removed, this exits `5` (`NOT_FOUND`). See
[Availability](/guides/availability/) for how to read the day fields and reconcile min-night
stretches.

---

## `nook reviews`

```text
nook reviews <listing_id> [--cursor]
```

Recent reviews for a listing, newest first. `--cursor` pages forward from a prior `nextCursor`.
Review `text` is fenced untrusted in agent mode by default — it's free text written by Airbnb
users, not instructions.

```bash
nook reviews 12345678 --json
```

```json
{
  "schemaVersion": 1,
  "scope": { "auth": "none", "corpus": "public-logged-out" },
  "data": [
    {
      "id": "998877",
      "author": "Marta",
      "rating": 5,
      "text": "‹untrusted-airbnb-content› Great location, very clean, host was responsive. ‹/untrusted-airbnb-content›",
      "date": "2026-05-12"
    }
  ],
  "nextCursor": null,
  "meta": { "count": 1, "truncated": false }
}
```

See [Reviews](/guides/reviews/) for the fencing rationale and [Pagination](/guides/pagination/)
for `--cursor` mechanics.

---

## `nook doctor`

```text
nook doctor
```

Diagnoses local setup: connectivity, transport (curl_cffi impersonation), and the
throttle/circuit-breaker state persisted under `$XDG_STATE_HOME/nook/`. Not enveloped as a read
result (no `scope`/`data`/`nextCursor` wrapper) — it emits a flat diagnostic object.

```bash
nook doctor --json
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

If any check fails, `doctor` exits `10` (`CONFIG`) instead of `0`. No network/auth flags — this
never contacts Airbnb beyond a basic connectivity probe.

---

## `nook schema`

```text
nook schema
```

Prints the full machine-readable command schema: the Click command tree, every flag, the
[exit-code table](/reference/exit-codes/), conformance metadata (`agent-cli-guidelines`, `Full`),
and a `safety` block confirming the mutation flags are inert. Use this to introspect nook
programmatically instead of parsing `--help` text — see [the schema-agent reference](/reference/schema-agent/).

```bash
nook schema --json | jq .conformance
```

```json
{ "spec": "agent-cli-guidelines", "version": "0.4.0", "level": "Full" }
```

---

## `nook agent`

```text
nook agent
```

Prints the bundled `SKILL.md` verbatim to stdout — the same guide an agent loads to learn nook's
command surface, safety contract, and legitimacy boundary in one shot. No JSON envelope; this is
raw markdown text, always.

```bash
nook agent
```

---

## `nook version`

```text
nook version [--check]
```

Without `--check`, prints the installed version:

```bash
nook version --json
```

```json
{ "version": "0.4.0" }
```

With `--check`, makes a short-timeout, fail-silent network call to look up the latest release and
reports whether an upgrade is available — it **never self-updates**, only reports the command to
run:

```bash
nook version --check --json
```

```json
{
  "current": "0.4.0",
  "latest": "0.4.1",
  "updateAvailable": true,
  "upgrade": "uv tool install --upgrade nook"
}
```

If the network check fails or times out, `latest` is `null` and a `"note": "could not check for
updates"` field is added — this is not an error, and the command still exits `0`. See
[Version check](/reference/version-check/) for the `NOOK_RELEASES_URL` override and its SSRF
guard.

---

## See also

- [Flags](/reference/flags/) — every global and net flag in one table.
- [Exit codes](/reference/exit-codes/) — the full mapping, with when each fires.
- [Output envelope](/concepts/output-envelope/) — the shape every read command shares.
- [Read-only](/concepts/read-only/) — why the mutation flags exist and do nothing.
