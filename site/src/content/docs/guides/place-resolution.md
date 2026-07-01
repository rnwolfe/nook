---
title: Place resolution
description: Resolve a fuzzy location string to a precise place ID, coordinates, and bounding box before searching.
---

`nook place search <query>` turns a fuzzy location string into a short list of place
candidates: a `placeId` and a `name` for each match, straight from Airbnb's own
autocomplete. It's the same lookup the airbnb.com search box uses when you start typing
a destination.

```bash
nook place search "Lisbon" --json
```

```json
{
  "schemaVersion": 1,
  "scope": { "auth": "none", "corpus": "public-logged-out" },
  "data": [
    {
      "placeId": "ChIJx8gPy5v_HA0R7VbEHY7NAAQ",
      "name": "Lisbon, Portugal",
      "type": "PLACE",
      "coordinates": null,
      "bbox": null
    },
    {
      "placeId": "ChIJi8mnMz9WGQ0RG9YZFQ0AAAA",
      "name": "Lisbon, NH, United States",
      "type": "PLACE",
      "coordinates": null,
      "bbox": null
    }
  ],
  "nextCursor": null,
  "meta": { "count": 2, "truncated": false }
}
```

## Do you actually need this?

Usually not. `nook search <location>` already accepts a raw string and resolves it
server-side:

```bash
nook search "Lisbon" --json
```

`nook place search` is a convenience for the cases where a bare string is ambiguous or
where you want to pin down exactly *which* Lisbon (or Springfield, or Portland) you
mean before you commit to a search — for example, disambiguating between candidates and
then handing the winning `placeId` to `nook search --place-id`:

```bash
nook place search "Lisbon" --json | jq -r '.data[0].placeId'
# ChIJx8gPy5v_HA0R7VbEHY7NAAQ

nook search "Lisbon" --place-id ChIJx8gPy5v_HA0R7VbEHY7NAAQ --checkin 2026-08-01 \
  --checkout 2026-08-05 --guests 2 --json
```

If you already know the place is unambiguous, skip the round trip and pass the location
string directly to `nook search`. Reach for `place search` when you need to disambiguate,
or when you're scripting a pipeline and want a stable `placeId` instead of re-parsing a
free-text location on every run.

## What's in each candidate

| Field | Notes |
|---|---|
| `placeId` | Google place ID for the match. Feed this to `nook search --place-id`. |
| `name` | Human-readable place name (e.g. `"Lisbon, Portugal"`). |
| `type` | Airbnb's autocomplete term type (e.g. `PLACE`). |
| `coordinates` | Always `null`. Airbnb's autocomplete endpoint doesn't expose lat/lng. |
| `bbox` | Always `null`, for the same reason. |

`coordinates` and `bbox` are declared in the shape but always come back `null` — Airbnb's
autocomplete only hands back a place ID and a name, not geometry. If you need a bounding
box for a map search, you'll need to supply your own (`--bbox` on `nook search`) rather
than expecting `place search` to produce one.

## No results

An ambiguous or nonsense query can legitimately resolve to an empty list — the command
still exits `0`, with `data: []` and `meta.count: 0`. Check `meta.count` (or just the
length of `data`) rather than relying on a distinct exit code for "no matches."

## Network backpressure

`nook place search` hits Airbnb like any other network command, so it accepts `--wait` (block
until the circuit breaker clears instead of failing fast) and `--max-wait SECONDS` (default
`900`). See [Rate limited](/troubleshooting/rate-limited/).

## Related

- [Searching](/guides/searching/) — pass a resolved `placeId` (or a raw location) into
  `nook search`.
- [Output envelope](/concepts/output-envelope/) — the `schemaVersion`/`scope`/`data`
  wrapper every read command shares.
- [Command reference](/reference/commands/) — full flag list for `nook place search`.
