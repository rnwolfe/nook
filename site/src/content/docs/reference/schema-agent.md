---
title: schema & agent
description: Discover nook's contract from the binary — nook schema emits machine JSON, nook agent prints the embedded guide.
---

An agent shouldn't have to guess nook's flags, exit codes, or safety posture by reading source or
docs. nook ships two commands that answer those questions from the binary itself:

- **`nook schema`** — the full command tree, every flag, the exit-code table, and a conformance
  block, as one JSON object.
- **`nook agent`** — the bundled `SKILL.md` (the same file this page's source list points at),
  printed verbatim to stdout, so an agent can load it into context at session start.

Both are read commands, but neither is wrapped in the usual [output envelope](/concepts/output-envelope/)
(no `schemaVersion`/`data`/`nextCursor`). They're meta commands describing the tool, not data reads
— `nook schema --json` prints its object straight to stdout, and `nook agent` prints raw Markdown.

## `nook schema`

```bash
nook schema --json
```

Top-level shape:

```json
{
  "tool": "nook",
  "version": "0.0.1",
  "conformance": {
    "spec": "agent-cli-guidelines",
    "version": "0.4.0",
    "level": "Full"
  },
  "readOnly": true,
  "scope": {
    "auth": "none",
    "corpus": "public-logged-out"
  },
  "commands": { "...": "Click's to_info_dict() tree — see below" },
  "exit_codes": { "...": "the stable exit-code table" },
  "safety": {
    "allow_mutations": false,
    "dry_run": false,
    "no_input": false,
    "note": "nook is read-only; mutation flags are inert (no command mutates)"
  }
}
```

### `conformance`

`{"spec": "agent-cli-guidelines", "version": "0.4.0", "level": "Full"}`. nook was born pinned to
this spec version at scaffold time — check it once at session start to confirm you're driving the
contract you expect, no version-sniffing heuristics needed.

### `readOnly` and `scope`

`readOnly: true` is a hard, static declaration — nook has no code path that mutates Airbnb.
`scope` is the same `{"auth": "none", "corpus": "public-logged-out"}` object that rides in every
read envelope's `scope` field (see [output envelope](/concepts/output-envelope/)): a reminder that
every result comes from the logged-out public view, not an authenticated or complete corpus.

### `commands`

The full command tree, straight from Click's `to_info_dict()` — every command, subcommand group
(`place`, `listing`), argument, and option with its type, default, and help text. Noun-verb groups
nest: `commands.commands.place.commands.search` is `nook place search` (the outer `commands` is
this schema field itself; the inner `commands` is Click's own nesting inside the tree). This is
exhaustive and mechanical; if you want prose instead, see [Commands](/reference/commands/) or the
table below.

```bash
nook schema --json | jq '.commands.commands | keys'
```

```json
["agent", "availability", "doctor", "listing", "place", "reviews", "schema", "search", "version"]
```

Drill into one command's options:

```bash
nook schema --json | jq '.commands.commands.availability.params[] | {name, opts, help}'
```

### `exit_codes`

The same table documented in [Exit codes](/reference/exit-codes/), as machine JSON so an agent can
branch on names instead of memorizing numbers:

```json
{
  "ok": 0,
  "generic_error": 1,
  "usage": 2,
  "empty_results": 3,
  "auth_required": 4,
  "not_found": 5,
  "permission": 6,
  "rate_limited": 7,
  "retryable": 8,
  "config_error": 10,
  "mutation_blocked": 12,
  "input_required": 13,
  "upstream_drift": 20,
  "cancelled": 130
}
```

`auth_required` (4), `permission` (6), and `mutation_blocked` (12) are present for contract
uniformity with other agent CLIs but are N/A for nook — it never returns them in normal use.

### `safety` — live, not static

`safety` isn't a fixed description of nook's defaults — it reflects the flags you actually passed
to *this* `schema` invocation. Pass the mutation flags and watch them flip:

```bash
nook schema --allow-mutations --dry-run --no-input --json | jq .safety
```

```json
{
  "allow_mutations": true,
  "dry_run": true,
  "no_input": true,
  "note": "nook is read-only; mutation flags are inert (no command mutates)"
}
```

They report as set — but the `note` still holds: nook has no mutating code path, so setting them
changes nothing. This is the whole "contract uniformity" story in one field: the flags exist so
nook is shaped like every other tool in the fleet, and `schema` tells you, truthfully, that they're
wired but dead here. See [read-only](/concepts/read-only/) for why.

## `nook agent`

```bash
nook agent
```

Prints the bundled `SKILL.md` (packaged data, loaded via `importlib.resources` — no network, no
filesystem guessing) straight to stdout as Markdown. It's the same content as nook's `SKILL.md`
source file: when-to-use guidance, the output contract, the command list, safety/etiquette notes,
the legitimacy boundary, and the exit-code cheat sheet — condensed to what an agent needs to drive
nook correctly without reading these docs.

Load it once per session instead of guessing:

```bash
nook agent > /tmp/nook-skill.md   # or pipe straight into context
```

Because it's plain Markdown (not JSON), `--json`/`--format` don't reshape it — `nook agent` always
prints the same text regardless of global flags.

## How an agent should self-orient

A cold-start agent that has never seen nook's docs can bootstrap in two calls:

1. `nook agent` — read the guide once; it's short and covers the whole contract.
2. `nook schema --json | jq .conformance,.exit_codes` — confirm the spec version and get the
   exit-code table as data, not prose, for branching logic.

`nook doctor --json` is the third leg (connectivity, transport, circuit-breaker state) — see
[rate-limited](/troubleshooting/rate-limited/) — but `schema` and `agent` are what answer "what can
this tool do and how do I call it," without guessing a single flag name.
