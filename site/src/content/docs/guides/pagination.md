---
title: Pagination
description: Page through results with the opaque cursor echoed back as nextCursor.
---

Two commands return more results than fit in one page: `nook search` and `nook reviews`. Both
follow the same pattern — the envelope's `nextCursor` field tells you whether there's more, and
you pass it straight back with `--cursor` to fetch the next page.

```json
{
  "schemaVersion": 1,
  "scope": { "auth": "none", "corpus": "public-logged-out" },
  "data": [ /* ... listings or reviews ... */ ],
  "nextCursor": "eyJzZWN0aW9uT2Zmc2V0IjoxfQ==",
  "meta": { "count": 20, "truncated": false }
}
```

## The rule: opaque in, opaque out

Never parse, decode, or construct a cursor yourself. Treat it as a black box — take whatever
string `nextCursor` gives you and hand it back verbatim on the next call:

```bash
nook search "Austin, TX" --format json > page1.json
cursor=$(jq -r '.nextCursor' page1.json)
nook search "Austin, TX" --cursor "$cursor" --format json > page2.json
```

The two commands don't build their cursors the same way under the hood, but that's an
implementation detail you shouldn't rely on:

- **`nook search`** echoes Airbnb's own upstream page token straight through
  (`paginationInfo.nextPageCursor` from the StaysSearch response).
- **`nook reviews`** doesn't get a cursor from Airbnb at all — the reviews query pages by numeric
  offset, so nook synthesizes its own cursor (the next offset, as a string) and hands it back to
  you the same way.

Both look like opaque strings in the envelope, and both round-trip the same way through
`--cursor`. Don't assume one is stable across nook versions or try to compute it out-of-band.

## `nextCursor: null` means you're done

When there's nothing left to page through, `nextCursor` is `null` (JSON) — no key to chase, no
more requests to make. This is the only reliable stop condition; don't stop just because a page
came back with fewer items than you expected (see `--limit` below).

A full drain loop for search:

```bash
location="Austin, TX"
cursor=""
all="[]"

while : ; do
  if [ -z "$cursor" ]; then
    resp=$(nook search "$location" --format json)
  else
    resp=$(nook search "$location" --cursor "$cursor" --format json)
  fi
  all=$(jq -s '.[0] + .[1].data' <(echo "$all") <(echo "$resp"))
  cursor=$(echo "$resp" | jq -r '.nextCursor // empty')
  [ -z "$cursor" ] && break
done

echo "$all" | jq 'length'
```

The same shape works for `nook reviews <id> --cursor <cursor>`.

## How `--limit` relates to the upstream page size

`--limit` (default `50`) bounds what nook *shows you*, not necessarily what it *fetched*. The two
commands relate `--limit` to the upstream page differently:

- **`search`** uses your `--limit` as a hint for the upstream page size, but clamps it into a
  sane band before asking Airbnb for a page: never smaller than 20, never larger than 50. So
  `--limit 5` still causes nook to request a page of roughly 20-50 results from Airbnb, then
  truncate the output to 5 client-side (with a loud note on stderr: `output truncated to 5 of 20
  items`). `--limit 500` gets capped to a 50-item upstream request, not a 500-item one.
- **`reviews`** always fetches 50 reviews per request from Airbnb regardless of `--limit` — the
  offset always advances by exactly 50 between pages. `--limit` only bounds what's emitted after
  that fetch.

The upshot: `--limit` controls the *output* size, not the pagination stride. Don't infer "more
pages exist" from `len(data) == limit`, and don't infer "no more pages" from getting back fewer
items than `--limit`. Only `nextCursor` tells you that. If you want the fetch size and the
display size to line up for search, pass the same `--limit` you plan to page with — but expect
the upstream floor of 20 regardless.

`--select` and `--concise`/`--detailed` apply to whatever page you already fetched; they don't
affect cursor advancement either.

## Worked example: paging reviews and merging

```bash
nook reviews 12345678 --format json | jq '{count: .meta.count, next: .nextCursor}'
```

```json
{ "count": 50, "next": "50" }
```

```bash
nook reviews 12345678 --cursor 50 --format json | jq '{count: .meta.count, next: .nextCursor}'
```

```json
{ "count": 12, "next": null }
```

`next: null` on the second call means that's the last page — 62 reviews total, done.

See [Searching listings](/guides/searching/) and [Reviews](/guides/reviews/) for the full filter
and field surface of each command, [The output envelope](/concepts/output-envelope/) for the rest
of the envelope shape, and [Bounding output](/guides/bounding-output/) for more on `--limit` and
`--select`.
