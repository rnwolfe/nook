---
title: Read-only & booking-excluded
description: nook never mutates and never books — mutation flags are inert no-ops, and transactions are out of scope by design.
---

`nook` is **100% read-only**. Every command it ships — `search`, `place search`, `listing get`,
`availability`, `reviews`, `doctor`, `schema`, `agent`, `version` — reads data. None of them
changes anything on Airbnb: no booking, no messaging, no wishlist edits, no account changes.
There is nothing in `nook` that can accidentally reserve a night, charge a card, or contact a host.

## Why booking is out of scope

Booking is the one action on Airbnb that actually mutates state — it moves money and creates a
real-world obligation. `nook`'s job is the piece agents are missing *before* that decision: search,
listing detail, and — its wedge — a forward [availability calendar](/guides/availability/) with
per-day price and minimum-nights, so an agent (or you) can figure out *where* and *when* to stay.
Once you know that, you book like a human, in the Airbnb app or on airbnb.com. `nook` deliberately
does not try to automate the transaction itself.

This isn't a missing feature — it's the design boundary. Keeping `nook` read-only also keeps its
[legitimacy story](/concepts/legitimacy/) simple: there's no login, no payment flow, no user
secrets to protect, and nothing an agent could do with `nook` that a human couldn't already do by
browsing the same public pages.

## The mutation gate exists, and it's a no-op

`nook` was built on the same scaffold as the rest of the agent-CLI fleet, and that scaffold assumes
some commands mutate. So `nook` carries the same mutation-gate machinery every fleet tool carries —
it's just never wired to anything, because there's no mutation to gate.

Concretely, in `src/nook/cli.py`, the `Runtime` dataclass has a `guard()` method:

```python
def guard(self, op: str) -> None:
    """Mutation gate — kept for contract uniformity. nook wires no mutations, so this is
    never reached in normal operation; the machinery exists (and is unit-tested) so the tool
    is structurally identical to gated members of the fleet."""
    if not self.allow_mutations:
        raise mutation_blocked(op)
```

No command in `nook` calls `rt.guard(...)`. It's unit-tested in isolation, but it never fires
during real use, because every command in `nook` is a read.

## The four mutation flags are inert no-ops

Every command accepts the full contract flag set via `global_options`, including four flags that
only make sense for a tool that mutates:

```text
--allow-mutations   Present for contract uniformity; no-op (nook is read-only).
--dry-run           Present for contract uniformity; no-op (nook is read-only).
--yes               Present for contract uniformity; no-op (nook is read-only).
--force             Present for contract uniformity; no-op (nook is read-only).
```

You can pass any of them to any command and nothing changes — no error, no behavior difference,
no output difference:

```bash
nook availability 12345678 --months 2 --allow-mutations --dry-run --yes --force --json
# identical output to: nook availability 12345678 --months 2 --json
```

They exist so `nook` presents the *same flag surface* as every other tool built to the
[Agent CLI Guidelines](https://aclig.dev) — an agent that has learned "pass `--allow-mutations` to
unblock a mutating command" on one tool in the fleet doesn't need a special case for `nook`. It's
just that for `nook`, that flag has nothing to unblock.

`nook schema --json` reports this explicitly, live, under `safety`:

```json
{
  "tool": "nook",
  "readOnly": true,
  "scope": { "auth": "none", "corpus": "public-logged-out" },
  "safety": {
    "allow_mutations": false,
    "dry_run": false,
    "no_input": false,
    "note": "nook is read-only; mutation flags are inert (no command mutates)"
  }
}
```

`nook agent` (the bundled skill file) states the same thing in prose for an agent reading it before
its first call.

## The exit code that goes with it is unreachable

The [exit code table](/reference/exit-codes/) reserves `12 MUTATION_BLOCKED` for the same reason —
contract uniformity — but `src/nook/errors.py` documents it as N/A up front:

```python
"""nook is 100% read-only. The auth/permission/mutation codes are present for contract
uniformity and documented as N/A; the target-specific addition is UPSTREAM_DRIFT (20)."""
```

Since no command ever calls `guard()`, `mutation_blocked()` (the helper that would raise it) is
never invoked in normal operation. If you see exit `12` out of `nook`, something is wrong with
`nook` itself, not your input. Alongside it, exit `4 AUTH` and `6 PERM` are also N/A — `nook` needs
[no auth](/getting-started/no-auth/) and has no permissioned resources to protect.

## What this means for you (or your agent)

- You never need `--allow-mutations` to get `nook` to do anything — every command already runs.
- `--dry-run`, `--yes`, and `--force` are safe to include defensively (e.g. a wrapper script that
  always passes them across a fleet of tools) — `nook` will just ignore them.
- If you want to actually book the stay `nook` found for you, do that in Airbnb's own app or site.
  `nook` will happily help you find it and confirm it's free; it will not press the button for you.
