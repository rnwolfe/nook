---
title: Exit codes
description: The stable exit-code table an agent can branch on — 0 ok, 3 empty, 5 not found, 7 rate-limited, 20 upstream drift, and more.
---

Every `nook` invocation ends with a process exit code. It's the first thing to branch on —
cheaper than parsing stderr, and stable across releases (contract §3). The table below matches
`errors.py`'s `ExitCode` class exactly, echoed verbatim by `nook schema --json` under
`exit_codes`.

```bash
nook listing get 0000000000 --json; echo "exit: $?"
```

```json
{"error": "listing 0000000000 not found", "code": "NOT_FOUND", "remediation": "verify the listing id — it may be invalid, private, or removed"}
```

```text
exit: 5
```

## The full table

| Code | Name | Meaning | When you'll see it |
| --- | --- | --- | --- |
| `0` | ok | Success. | The command produced output (including a valid, possibly empty, result set) and returned normally. |
| `1` | generic_error | Unclassified failure. | Any upstream 4xx that isn't a 403/429 challenge (`HTTP_ERROR`) — including a raw HTTP 404 from Airbnb — or any other error that doesn't map to a more specific code. |
| `2` | usage | Bad invocation. | Unknown flag, missing required argument, bad `--format` choice, etc. — Click rejected the command line before `nook` ever touched the network. |
| `3` | empty_results | Empty result set. | Reserved for "search / calendar returned nothing" (see note below — in the current release this surfaces as exit `0` with an empty `data` array and `meta.count: 0` instead; treat `0` + empty array as the practical empty signal today). |
| `4` | auth_required | N/A. | Never returned. nook needs no auth — see [No auth](/getting-started/no-auth/). Present for contract uniformity only. |
| `5` | not_found | Listing id invalid, private, or removed. | `nook listing get <id>` or `nook availability <id>` when the client parses the response and finds no listing at that id — this is nook's own detection (a page missing its embedded state, or a calendar with no data), not a raw HTTP 404 from Airbnb (a real 404 status surfaces as `generic_error`, exit `1`, instead). |
| `6` | permission | N/A. | Never returned. nook has no permissioned resources — every read is the public logged-out view. Present for contract uniformity only. |
| `7` | rate_limited | Airbnb blocked or challenged the request (403 / 429 / CAPTCHA). | The transport layer trips its circuit-breaker and raises immediately — it does **not** retry into a block. See [7 vs 20](#7-vs-20-blocked-vs-drifted) and [Rate limited](/troubleshooting/rate-limited/). |
| `8` | retryable | Transient upstream trouble. | Network error, 5xx after the built-in retry/backoff is exhausted, or a transient GraphQL `UPSTREAM_ERROR`. Safe to retry shortly; nook already backed off twice before surfacing this. |
| `10` | config_error | Local setup problem. | `nook doctor` when one or more checks fail (state dir unwritable, transport unreachable, etc). |
| `12` | mutation_blocked | N/A. | Never returned in normal use. The mutation gate (`Runtime.guard`) exists for contract uniformity — nook wires no mutating command, so nothing calls it. See [Read-only](/concepts/read-only/). |
| `13` | input_required | A required value was missing and `--no-input` was set. | Normally nook never prompts, so this only fires under `--no-input` where an interactive fallback would otherwise have asked. Pass the value explicitly. |
| `20` | upstream_drift | Airbnb changed something internal that nook depends on. | The public API key, a persisted-query hash, or a GraphQL response shape moved and self-healing couldn't recover. See [7 vs 20](#7-vs-20-blocked-vs-drifted) and [Upstream drift](/troubleshooting/upstream-drift/). |
| `130` | cancelled | You (or your agent framework) hit Ctrl-C. | `click.Abort` — standard `128 + SIGINT`. |

## 7 vs 20: blocked vs. drifted

These two look similar from the outside — "the request failed" — but they mean opposite things
and call for opposite responses. Don't conflate them.

**`7` (`RATE_LIMITED`)** means Airbnb's edge (HUMAN/PerimeterX) saw the request and didn't like the
*volume* — a 403, 429, or a "Press & Hold" CAPTCHA interstitial. nook's stance is to stop, not
evade: the circuit-breaker trips (state persisted in `$XDG_STATE_HOME/nook/`, since an agent
spawns a fresh process per call), and the command exits 7 immediately rather than retrying into
the block. **Do not loop on exit 7.** Wait, reduce volume, or pass `--wait` to block until the
breaker clears (up to `--max-wait` seconds, default 900). Full detail: [Rate limited](/troubleshooting/rate-limited/).

```json
{"error": "blocked by Airbnb (rate limit or bot challenge)", "code": "RATE_LIMITED", "remediation": "stop and retry later at lower volume; nook self-throttles and will not evade the block"}
```

**`20` (`UPSTREAM_DRIFT`)** means the request went through fine, network-wise — Airbnb just changed
the *shape* of something nook depends on internally: the scraped public `X-Airbnb-Api-Key`, a
persisted-query `sha256Hash` (the `StaysSearch` hash rotates and nook attempts one self-heal
re-scrape before giving up), or a GraphQL response's expected fields. This is nook's own bookkeeping
falling out of sync with Airbnb's SPA — not a block, and not something waiting or retrying fixes.
**The tool itself needs an update.** Full detail: [Upstream drift](/troubleshooting/upstream-drift/).

```json
{"error": "Airbnb's internal API shape changed: StaysSearch response missing the expected results node", "code": "UPSTREAM_DRIFT", "remediation": "update nook to a newer release (uv tool install --upgrade nook); this is not a rate limit"}
```

The short version an agent can branch on: **7 → back off**, **20 → upgrade nook**. Retrying a `20`
at lower volume will not help; it'll fail the same way every time until the tool ships a fix.

## 13: input required

nook doesn't have interactive prompts in the traditional sense, but the flag exists so an agent
loop can guarantee it never gets stuck waiting on stdin: pass `--no-input` and any place that
would otherwise fall back to asking instead fails fast with exit `13`.

```json
{"error": "listing_id is required", "code": "INPUT_REQUIRED", "remediation": "pass it as a flag/argument (running with --no-input, so prompts are disabled)"}
```

The fix is always the same: supply the missing value as a flag or argument and re-run.

## N/A: 4, 6, 12

Three codes exist purely for **contract uniformity** across the fleet of agent CLIs nook belongs
to, and are never returned by nook in normal use:

- **`4` (auth_required)** — nook needs no auth. Every read is public and logged-out; there's no
  credential to be missing. See [No auth](/getting-started/no-auth/).
- **`6` (permission)** — nook has no permissioned resources to be denied access to.
- **`12` (mutation_blocked)** — nook has no mutating commands. The mutation gate
  (`Runtime.guard`, wired to `--allow-mutations`/`--dry-run`/`--yes`/`--force`) is implemented and
  unit-tested so the tool is structurally identical to gated members of the fleet, but no command
  calls it. See [Read-only](/concepts/read-only/).

If you ever see one of these three from a real `nook` invocation, that's a bug — file it.

## The error envelope

Every non-zero exit except `2` (usage) and `130` (cancelled) prints a structured error to
**stderr** before the process exits. In `--json`/`--format json` mode it's a single JSON object:

```json
{"error": "<human message>", "code": "<MACHINE_CODE>", "remediation": "<what to do next>"}
```

In `plain`/`tsv` mode the same three fields print as labeled lines instead:

```text
error: listing 0000000000 not found
  code: NOT_FOUND
  fix:  verify the listing id — it may be invalid, private, or removed
```

**Exception:** usage errors (exit `2`) are raised by Click before nook's own runtime/format is
even constructed, so they always print as plain `error: <message>` text to stderr — regardless of
`--format`. Don't expect a JSON envelope for exit `2`; parse it as text or just check the exit
code and stop.

`stdout` is reserved for `data` — nothing above ever writes there. See
[The output envelope](/concepts/output-envelope/) for the success-path shape.

## Branching guidance for agents

A minimal decision tree:

```text
exit 0   → parse stdout as the envelope; check meta.count / meta.truncated
exit 3   → (reserved) treat as "no results"; today this surfaces as exit 0 + empty data array
exit 5   → the id was wrong/private/removed; don't retry with the same id
exit 7   → STOP retrying; back off, or re-run with --wait
exit 8   → transient; a short retry is reasonable
exit 13  → fill in the missing flag/argument and re-run
exit 20  → stop retrying; the fix is `uv tool install --upgrade nook`, not backoff
anything else → surface the error/code/remediation to the operator
```

`nook schema --json | jq .exit_codes` prints this table straight from the running binary, so an
agent never has to hardcode it. Related: [Schema & agent mode](/reference/schema-agent/),
[Commands](/reference/commands/), [Flags](/reference/flags/).
