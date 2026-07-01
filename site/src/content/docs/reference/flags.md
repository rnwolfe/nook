---
title: Flags
description: Global and per-command flags — output, bounding, pagination, currency, and the inert mutation flags.
---

`nook` attaches the global flags to **every** command (not just the root), so an agent can put
them anywhere on the command line:

```bash
nook search "Lisbon" --json
nook --json search "Lisbon"
```

Both work. Values are merged leaf-first across the command chain, so a flag set on the subcommand
wins over the same flag set on the group.

## Global flags

These apply to every command.

| Flag | Type | Default | Notes |
|---|---|---|---|
| `--format <json\|plain\|tsv>` | choice | `plain` (`json` if stdout isn't a TTY... see below) | Output format. |
| `--json` | flag | off | Shorthand for `--format json`. |
| `--no-color` | flag | off | Disable colored output. Color is only ever on for `plain` on an interactive TTY anyway. |
| `--limit <N>` | int | `50` | Bounds list results. `0` (or negative) disables bounding. See [Bounding output](/guides/bounding-output/). |
| `--select <a,b.c>` | string | none | Comma-separated dot-path field projection, applied to each item in `data`. See [Bounding output](/guides/bounding-output/). |
| `--concise` | flag | off | Accepted for contract uniformity. Parsed but not currently wired to change output — see note below. |
| `--detailed` | flag | off | Accepted for contract uniformity. Parsed but not currently wired to change output — see note below. |
| `--no-wrap` | flag | off | Disable fencing of untrusted Airbnb text. Fencing is default-ON in agent mode (JSON output, or any non-TTY stdout); default-OFF on the human plain-TTY path. See [Prompt-injection fencing](/concepts/legitimacy/) and the schema/agent references. |
| `--no-input` | flag | off | Never prompt; fail with exit `13` instead. `nook` doesn't currently have interactive prompts in the read paths, so this is here for contract uniformity and future-proofing. |
| `--allow-mutations` | flag | off | **Inert.** No command in `nook` mutates anything; this exists so the CLI's shape matches other tools in the fleet. |
| `--dry-run` | flag | off | **Inert**, same reason. |
| `--yes` | flag | off | **Inert**, same reason. |
| `--force` | flag | off | **Inert**, same reason. |
| `-h`, `--help` | flag | — | Standard Click help. |

A note on `--format` and TTY detection: the *default* format is `plain` unless you pass
`--json`/`--format json`. What changes with TTY-vs-pipe is the **fencing** behavior
(`--no-wrap`), not the format default — `nook` never silently switches your requested format.
If you don't pass `--format`/`--json` at all, you get `plain`.

### The inert flags, precisely

`nook` is read-only by design — see [Read-only](/concepts/read-only/). `--allow-mutations`,
`--dry-run`, `--yes`, and `--force` exist purely so `nook`'s contract surface matches every other
tool built to the same [Agent CLI Guidelines](https://aclig.dev). Internally there's a
`Runtime.guard()` mutation gate that would raise `mutation_blocked` if a command tried to mutate
without `--allow-mutations` — but no command ever calls it. Booking (the only real mutation
Airbnb exposes) is out of scope by design, not just gated off. Passing any of these four flags
changes nothing about `nook`'s behavior or output.

### `--concise` / `--detailed`: currently no-ops too

The brief for these two flags is "terser output" / "richer output," matching the shape of other
agent CLIs. As of this writing, `nook`'s code parses both flags (they're valid, and won't error)
but nothing in the output path branches on them — every command emits the same payload shape
regardless of `--concise`/`--detailed`. Don't rely on them to change what fields come back today;
use `--select` for field projection instead. (This is different from the mutation flags, which
are *deliberately* inert forever — these two are simply not yet wired.)

## Network-command flags

Every command that talks to Airbnb (`search`, `place search`, `listing get`, `availability`,
`reviews`) additionally accepts:

| Flag | Type | Default | Notes |
|---|---|---|---|
| `--wait` | flag | off | If the circuit-breaker is open (tripped by a prior block/rate-limit), block and poll until it clears instead of failing fast with exit `7`. |
| `--max-wait <SECONDS>` | float | `900` | Cap on how long `--wait` will block. |

By default `nook` fails fast on a tripped breaker (exit `7`) rather than retrying into a block —
see [Rate limited](/troubleshooting/rate-limited/). `--wait` is an explicit opt-in to block
instead:

```bash
nook availability 12345678 --months 2 --wait --max-wait 120 --json
```

`doctor`, `schema`, `agent`, and `version` do **not** hit Airbnb and don't take `--wait`/`--max-wait`.

## Per-command flags

### `nook search <location>`

The location argument is a bare string (e.g. `"Lisbon"`) and becomes the search query. Passing
`--bbox` or both `--lat`/`--lng` switches the backend to a map search instead of a text query.

| Flag | Type | Notes |
|---|---|---|
| `--checkin <YYYY-MM-DD>` | date | Check-in date. |
| `--checkout <YYYY-MM-DD>` | date | Check-out date. |
| `--guests <N>` | int | Total guests. |
| `--adults <N>` | int | Adult count. |
| `--children <N>` | int | Children count. |
| `--infants <N>` | int | Infant count. |
| `--pets <N>` | int | Pet count. |
| `--min-price <N>` | int | Minimum nightly price. |
| `--max-price <N>` | int | Maximum nightly price. |
| `--room-type <entire\|private\|shared\|hotel>` | choice | Room type filter. |
| `--bedrooms <N>` | int | Minimum bedrooms. |
| `--beds <N>` | int | Minimum beds. |
| `--bathrooms <N>` | int | Minimum bathrooms. |
| `--amenities <a,b>` | string | Comma-separated amenities filter. |
| `--superhost` | flag | Only Superhost listings. |
| `--place-id <id>` | string | A resolved place id from `nook place search`, for deterministic (non-fuzzy) location targeting. |
| `--lat <float>` | float | Latitude, paired with `--lng`, for point/map search. |
| `--lng <float>` | float | Longitude, paired with `--lat`. |
| `--bbox <neLat,neLng,swLat,swLng>` | string | Bounding box — switches to map search. See [Bounding output](/guides/bounding-output/) (note: this is a geographic bbox, distinct from output bounding). |
| `--currency <ISO>` | string | e.g. `USD`. Also controls the `meta.currency` on the envelope. |
| `--sort <value>` | string | Sort order; backend default if omitted. |
| `--cursor <token>` | string | Opaque pagination cursor from a prior response's `nextCursor`. See [Pagination](/guides/pagination/). |

Plus [global flags](#global-flags) and [network flags](#network-command-flags).

```bash
nook search "Lisbon" --checkin 2026-08-01 --checkout 2026-08-05 --guests 2 \
  --room-type entire --min-price 80 --max-price 220 --json
```

See [Searching](/guides/searching/).

### `nook place search <query>`

No command-specific flags beyond [global](#global-flags) and [network](#network-command-flags).

```bash
nook place search "Lisbon" --json
```

See [Place resolution](/guides/place-resolution/).

### `nook listing get <listing_id>`

No command-specific flags beyond [global](#global-flags) and [network](#network-command-flags).

```bash
nook listing get 12345678 --json
```

See [Listing details](/guides/listing-details/).

### `nook availability <listing_id>`

| Flag | Type | Default | Notes |
|---|---|---|---|
| `--months <1..12>` | int | `1` | Forward months of calendar to fetch. Mutually exclusive in effect with `--start`/`--end` — if both are given, `--start`/`--end` override the `--months` window. |
| `--start <YYYY-MM-DD>` | date | none | Explicit window start. |
| `--end <YYYY-MM-DD>` | date | none | Explicit window end. |
| `--currency <ISO>` | string | none | Controls day-level `price.currency` and `meta.currency`. |

Plus [global flags](#global-flags) and [network flags](#network-command-flags).

```bash
nook availability 12345678 --months 3 --currency USD --json
nook availability 12345678 --start 2026-09-01 --end 2026-09-30 --json
```

See [Availability](/guides/availability/).

### `nook reviews <listing_id>`

| Flag | Type | Notes |
|---|---|---|
| `--cursor <token>` | string | Opaque pagination cursor from a prior response's `nextCursor`. |

Plus [global flags](#global-flags) and [network flags](#network-command-flags).

```bash
nook reviews 12345678 --json
```

Review text is fenced as untrusted content by default in agent mode — see
[Reviews](/guides/reviews/).

### `nook doctor`

Only [global flags](#global-flags). Does not hit Airbnb (checks connectivity/transport/throttle
state), so no `--wait`/`--max-wait`.

```bash
nook doctor --json
```

### `nook schema`

Only [global flags](#global-flags). See [Schema (agent)](/reference/schema-agent/).

```bash
nook schema --json
```

### `nook agent`

Only [global flags](#global-flags) (though the output is raw Markdown text, not JSON, regardless
of `--format`). Prints the bundled `SKILL.md`.

```bash
nook agent
```

### `nook version`

| Flag | Type | Notes |
|---|---|---|
| `--check` | flag | Check the latest release (network, short timeout, fail-silent). Without it, just prints the current version. |

```bash
nook version
nook version --check --json
```

See [Version check](/reference/version-check/).

## Quick defaults reference

| Flag | Default |
|---|---|
| `--format` | `plain` |
| `--limit` | `50` |
| `--months` (availability) | `1` |
| `--max-wait` | `900` seconds |
| `--wait` | off (fail fast) |
| `--no-wrap` | off (fencing is on in agent mode; off on human plain-TTY) |
| `--no-color` | off |
| `--allow-mutations` / `--dry-run` / `--yes` / `--force` | off, and always inert |
