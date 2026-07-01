---
title: Bounding output for agents
description: Keep responses inside an agent's context budget with --limit and --select field projection.
---

Airbnb pages come back fat: a search result item alone can carry dozens of fields (photos, host
metadata, badges, pricing breakdowns…) and an availability call can span a year of per-day
records. An agent burning its context window on fields it never reads is the real cost. `nook`
gives you four levers to shape output before it ever hits your context: `--limit`, `--select`,
`--format`, and `--concise`/`--detailed`. Use them together.

## `--limit N` — cap how many items come back

Every list-shaped read (`search`, `availability`, `reviews`, `place search`) is bounded by
`--limit`, **default 50**. It's a global flag, so it works on any command:

```bash
nook search "Lisbon" --checkin 2026-08-01 --checkout 2026-08-05 --limit 10 --json
```

Bounding happens in `Writer.emit_read` (`src/nook/output.py`), after `--select` projection: it
counts the payload, and if it's a list longer than the limit, it slices to `g[:limit]` and sets
`"truncated": true` in `meta`. Truncation is **loud**, not silent — a note goes to stderr so a
human watching the terminal sees it, but it never pollutes stdout:

```text
note: output truncated to 10 of 47 items (use --limit to change, or page with --cursor)
```

The JSON envelope tells the same story on stdout, so an agent parsing `--json` output doesn't
need to watch stderr to know it got a partial page:

```json
{
  "schemaVersion": 1,
  "scope": {"auth": "none", "corpus": "public-logged-out"},
  "data": [ /* 10 listings */ ],
  "nextCursor": "eyJvZmZzZXQiOjEwfQ==",
  "meta": {"count": 10, "truncated": true, "total": 47, "currency": "USD"}
}
```

`meta.count` is how many items are actually in `data`; `meta.total` (present whenever the
untrimmed payload was a list) is how many there were before slicing. When `meta.truncated` is
`true`, `nextCursor` is your way forward — see [Pagination](/guides/pagination/) for the cursor
model, and pass it back with `--cursor`.

`--limit 0` disables the cap entirely (the check is `self.limit > 0`) — every matching item comes
back in one shot. That's rarely what you want against a live search that can return dozens of
listings; reach for it deliberately, and prefer paging with `--cursor` for anything large.

`--limit` also bounds non-envelope output — `nook schema`, `nook doctor`, `nook version` go
through the same `Writer.emit` path (`_apply_limit`) if their payload happens to be a list, though
in practice those commands return small, fixed-shape objects.

## `--select a,b.c` — project only the fields you need

`--select` is a comma-separated list of dot-paths, applied to each item in `data` *before* the
limit is applied. It's implemented by `_apply_select` / `_get_path` in `src/nook/output.py`: each
path is walked key-by-key through nested dicts, and only paths that resolve are kept, using the
**full dotted path as the output key** (it does not rename or flatten):

```bash
nook search "Lisbon" --select name,price.amount,price.currency --limit 5 --json
```

```json
{
  "schemaVersion": 1,
  "scope": {"auth": "none", "corpus": "public-logged-out"},
  "data": [
    {"name": "Sunny flat near Alfama", "price.amount": 87, "price.currency": "USD"},
    {"name": "Modern loft, Príncipe Real", "price.amount": 142, "price.currency": "USD"}
  ],
  "nextCursor": null,
  "meta": {"count": 5, "truncated": false, "currency": "USD"}
}
```

A path that doesn't exist on a given item is simply omitted from that item's object (no `null`
padding, no error) — `_get_path` returns `(False, None)` and `_select_obj` skips it. That means
`--select` is safe to use speculatively across heterogeneous items (e.g. some listings have
`host.isSuperhost`, others don't) without crashing the command.

`--select` also applies to `availability`'s per-day rows and `reviews`' items — anywhere a list of
dicts is the payload:

```bash
nook availability 12345678 --months 2 --select date,available,price.amount --json
```

If the resolved payload is a single object rather than a list (e.g. `nook listing get`), the same
projection still applies — `_apply_select` calls `_select_obj` directly on the dict.

## `--format json|plain|tsv` — pick the shape for the consumer

`--format` (or its `--json` shorthand for `--format json`) controls how the *same* bounded/
projected data is rendered:

- **`json`** — the full envelope (`schemaVersion`, `scope`, `data`, `nextCursor`, `meta`) as
  pretty-printed JSON on stdout. This is the agent path — always use it in automation.
- **`plain`** — human-friendly. Only the `data` payload is rendered, as an aligned, whitespace-padded
  table (list-of-dicts → union of keys as headers; scalars → one per line). Envelope metadata
  (truncation notes, `nextCursor` hints) goes to stderr instead of stdout, per `emit_read`'s human
  path in `output.py`.
- **`tsv`** — same payload-only rendering as `plain`, but tab-separated and unaligned — built for
  piping into `cut`/`awk`/a spreadsheet, not for reading in a terminal.

```bash
nook search "Lisbon" --format tsv --select name,price.amount --limit 5
```

```text
name	price.amount
Sunny flat near Alfama	87
Modern loft, Príncipe Real	142
```

Default format (no `--format`/`--json`) is `plain`. Agents should always pass `--json` — it's the
only format that carries `meta`/`nextCursor` on stdout, and it's the shape every other guide in
these docs assumes. See [The output envelope](/concepts/output-envelope/) for the full envelope
contract.

## `--concise` / `--detailed`

Both flags are part of nook's global option surface (parsed and merged across the command chain
like every other global flag), present for contract uniformity with the wider agent-CLI
guidelines. As of this writing, no command branches on them to change payload shape — nook's
default output is already the concise, agent-sized shape, and `--select`/`--limit` are how you
actually reshape it. Treat `--concise`/`--detailed` as reserved/no-op today; the flag names are
stable if that changes, so passing `--concise` won't break anything, it just won't do more than
the defaults already do.

## Putting it together

The tight-context recipe for an agent loop is: pick only the fields you'll act on, cap the count
to what you'll actually consider, and always go through `--json` so truncation is visible in
`meta` rather than only shouted to a stderr stream you might not be capturing:

```bash
nook search "Lisbon" \
  --checkin 2026-08-01 --checkout 2026-08-05 --guests 2 \
  --select name,price.amount,price.currency,roomType \
  --limit 10 \
  --json
```

That single call bounds both the *width* (fields) and the *height* (item count) of what lands in
your context — and the envelope's `meta.truncated` / `meta.total` / `nextCursor` tell you exactly
what you didn't see, so you can decide whether to page with `--cursor` (see
[Pagination](/guides/pagination/)) or narrow your filters instead (see
[Searching](/guides/searching/)).
