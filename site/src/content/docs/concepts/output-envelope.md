---
title: The output envelope
description: Every read returns a stable envelope — schemaVersion, scope, data, nextCursor, and meta.
---

Every read command in nook returns the same shape. Not "similar." The same. `nook search`,
`nook place search`, `nook listing get`, `nook availability`, and `nook reviews` all wrap
their payload in one envelope, so an agent can write one parser and reuse it across every
command:

```json
{
  "schemaVersion": 1,
  "scope": { "auth": "none", "corpus": "public-logged-out" },
  "data": [],
  "nextCursor": null,
  "meta": { "count": 0, "truncated": false }
}
```

This comes from `Writer.emit_read()` in `src/nook/output.py`, and it's the one function every
read command calls on its way out. `nook doctor`, `nook schema`, and `nook version` are
diagnostics, not reads — they emit via `Writer.emit()`/`emit_json()` without an envelope, because
there's no corpus scope or pagination to declare for them. `nook agent` is different again: it
writes the bundled `SKILL.md` guide straight to stdout as plain text, bypassing `Writer`
entirely — there's no JSON at all on that path.

## The five fields

**`schemaVersion`** — currently `1`. It only bumps on a breaking change to the envelope
shape itself (see append-only, below). Pin your parser to it; if it's ever `2`, don't assume
your existing field access still works.

**`scope`** — `{"auth": "none", "corpus": "public-logged-out"}` on every single response, no
exceptions. nook makes zero authenticated requests — see
[No auth, by design](/getting-started/no-auth/) — so this pair never changes for the life of
the tool. It's declared inline anyway, on every envelope, so an agent parsing one search
result three hours from now never has to guess whether it's looking at a partial, logged-out
view or a complete one. It's always the logged-out view. See
[Read-only, by design](/concepts/read-only/) for the sibling guarantee on the write side.

**`data`** — the actual payload. A JSON array for `search`, `place search`, `availability` (one
entry per day), and `reviews`; a single object for `listing get`. `--select` and `--limit`
(below) only ever touch this field — they never touch `scope` or `meta`.

**`nextCursor`** — an opaque pagination token, or `null` if there's nothing more to fetch. Only
`search` and `reviews` currently populate it (both accept `--cursor`); `listing get` and
`availability` always emit `null` here since they aren't paginated result sets. Never construct
or parse this string — treat it as a black box and pass it straight to `--cursor` on the next
call. See [Pagination](/guides/pagination/).

**`meta`** — bookkeeping about `data`, not part of the data itself:

- `count` — items in `data` after `--limit` was applied (or `1` for a single-object payload).
- `truncated` — `true` if `--limit` cut the list short.
- `total` — present only when the payload is a list: the *pre-truncation* size, so you can tell
  "50 of 50" from "50 of 312."
- Extra keys some commands add: `search` and `availability` add `"currency"` (echoing back the
  currency prices are quoted in, defaulting to `"USD"` if you didn't pass `--currency`).

## Append-only, not additive-forever

The contract nook makes is: **existing fields never change meaning, and are never removed,
without a `schemaVersion` bump.** New fields can and will show up in `meta` or on individual
`data` items over time — that's a compatible change and does *not* bump the version. What
*would* bump it: renaming `data` to something else, changing `nextCursor` from a string to an
object, or making `scope` mean something different. Write your parser to ignore fields it
doesn't recognize, and you won't need to touch it when nook adds one.

## stdout is data, stderr is everything else

This is the load-bearing part for scripting and piping. With `--format json` (or its alias
`--json`), the **entire envelope** — all five fields — goes to stdout as one JSON document, and
stdout carries nothing else. Anything informational goes to stderr instead:

```bash
nook availability HABBQ12345 --months 2 --json 2>/dev/null
```

That command's stdout is valid, parseable JSON — nothing else is mixed in — because `2>/dev/null`
threw away the "note: more results available" and truncation warnings that would otherwise land
on stderr.

On the **human plain/tsv path** (no `--json`), the rendering is inverted for readability: stdout
gets just the `data` payload rendered as a table (or scalar lines), and the envelope's metadata —
truncation notes, `nextCursor` follow-up hints — moves to stderr as `note:` lines. Either way, the
split holds: **stdout is data, stderr is chatter.** This is why `nook search Lisbon | jq '.data'`
only works with `--json`; the plain-format stdout is already bare data with no envelope to
`jq` into.

```bash
$ nook search Lisbon --limit 2
id        name                          price      rating
12345678  Sunny loft near Alfama        84 USD     4.92
23456789  Rooftop studio, river view    112 USD    4.85
```

```text
note: output truncated to 2 of 47 items (use --limit to change, or page with --cursor)
```

(The table went to stdout; the truncation note went to stderr — that's why it's shown
separately above.)

## Errors: no envelope, stderr only, mapped exit code

Errors never appear inside `data`, and they never get an envelope. An `AppError` always writes
to stderr and the process exits with the error's mapped code (see
[Exit codes](/reference/exit-codes/)). In JSON mode the shape is a flat three-field object:

```json
{
  "error": "listing 999999999999 not found",
  "code": "NOT_FOUND",
  "remediation": "verify the listing id — it may be invalid, private, or removed"
}
```

```bash
$ nook listing get 999999999999 --json
$ echo $?
5
```

(stdout above is empty — the error object went to stderr — and the exit code is `5`,
`NOT_FOUND`.) In plain mode the same three fields print as labeled lines instead of JSON:

```text
error: listing 999999999999 not found
  code: NOT_FOUND
  fix:  verify the listing id — it may be invalid, private, or removed
```

## How `--select` and `--limit` apply

Both flags act on `data` only — never on `scope`, `nextCursor`, or the envelope shape.

- **`--select a,b.c`** takes a comma-separated list of dot-paths and projects each item in
  `data` down to just those paths (nested lookups like `host.name` are supported via the dot).
  The result is a flat object keyed by the path string itself — e.g.
  `--select price.amount,rating` on a search result turns each listing into
  `{"price.amount": 84, "rating": 4.92}`, dropping every other field. A missing path is simply
  omitted from that item's output, not filled with `null`. This runs *before* the limit/
  truncation accounting.
- **`--limit N`** (default `50`) caps how many items from a list-shaped `data` survive into the
  response. This applies to every list-shaped command — including `nook availability`, where a
  wide `--months` window can produce more days than the default limit and get silently cut down
  unless you raise `--limit`. If the underlying result has more than `N` items, `meta.truncated`
  becomes `true`, `meta.total` records the pre-truncation count, and a `note:` line goes to
  stderr telling you to raise `--limit` or page with `--cursor`. `--limit 0` disables truncation.
  `listing get` returns a single object, not a list, so `--limit` has nothing to truncate there.
  `--limit` never changes `meta.count`'s *meaning* — it's always "items actually present in
  `data`," post-truncation.

See [Bounding output](/guides/bounding-output/) for `--select`/`--limit` in more depth, and
[Pagination](/guides/pagination/) for how `nextCursor` and `--cursor` chain across calls.
