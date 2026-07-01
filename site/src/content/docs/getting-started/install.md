---
title: Installation
description: Install nook with uvx for a zero-install trial or uv tool install for repeated agent use — a single Python/Click CLI on PyPI, Python 3.10+.
---

`nook` is a single Python package published to [PyPI](https://pypi.org/project/nook/). There's no
API key to configure and no login step — see [No auth required](/getting-started/no-auth/) — so
installing it is the whole setup.

## Requirements

- Python **3.10+**
- [uv](https://docs.astral.sh/uv/) (recommended) — or `pip`/`pipx` if you don't have `uv`

There's no Homebrew formula yet. If you're on a Mac and want a `brew install`, use `uv` or `pipx`
in the meantime — both work fine.

## Try it with no install

If you just want to run one command — kicking the tires, or a one-shot call from an agent loop
that doesn't own its own environment — use `uvx`. It downloads `nook`, runs it, and doesn't leave
anything installed:

```bash
uvx nook search "Lisbon" --checkin 2026-08-01 --checkout 2026-08-05 --guests 2 --json
```

Every `uvx nook ...` invocation re-resolves the package. That's fine for a single call, but it adds
resolve overhead if you're calling `nook` repeatedly in a loop — see below.

## Install for repeated / agent use

If an agent (or you) will be calling `nook` more than a few times — a search loop, a scheduled
availability check, anything long-running — install it once as a persistent tool instead:

```bash
uv tool install nook
```

This puts a bare `nook` on your `PATH`:

```bash
nook search "Lisbon" --json
nook availability 12345678 --months 3 --json
```

Prefer `uv tool install` for anything that isn't a single throwaway call — it skips the
per-invocation resolve that `uvx` pays every time.

Don't have `uv`? `pipx install nook` works the same way (isolated environment, `nook` on `PATH`).
A plain `pip install nook` into an existing environment works too, but isolated installs
(`uv tool` / `pipx`) are recommended so `nook`'s dependencies don't collide with a project's.

## Upgrading

```bash
uv tool install --upgrade nook
```

`nook` never upgrades itself — see [`version --check`](/reference/version-check/) for how it tells
you an upgrade exists without ever running one for you.

## Verify the install

Two commands confirm nook is installed and working, with no network call and no auth required.

Check the version:

```bash
nook version
```

```json
{
  "version": "0.0.1"
}
```

The version tracks the installed package (`nook`'s current pyproject version at time of writing
is `0.0.1`; expect this to climb as releases ship). If you installed from a git checkout rather
than a packaged release, this may read `"dev"` instead of a version number — expected, and
`version --check` treats `"dev"` as never having an update available.

Then confirm the full command surface and conformance level:

```bash
nook schema --json
```

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
  "scope": { "auth": "none", "corpus": "public-logged-out" },
  "commands": { "...": "full command tree" },
  "exit_codes": { "...": "..." },
  "safety": {
    "allow_mutations": false,
    "dry_run": false,
    "no_input": false,
    "note": "nook is read-only; mutation flags are inert (no command mutates)"
  }
}
```

`nook schema | jq .conformance` is the fast check that you're on a build that conforms to the
[Agent CLI Guidelines](https://aclig.dev) at level Full. Note that `version` and `schema` (like
`doctor` and `agent`) print a plain JSON object, not the read envelope — there's no `scope`/`data`
wrapper here, because these are introspection commands, not data reads. The read commands
(`search`, `listing get`, `availability`, `reviews`, `place search`) always carry the full envelope
— see [The output envelope](/concepts/output-envelope/).

For a local health check — confirming the TLS-impersonation transport is available, the
throttle/circuit-breaker state is clean, and the scraped key cache status — run:

```bash
nook doctor
```

This doesn't make a network call itself; it inspects the same on-disk state (and package
imports) that the network commands rely on. See [No auth](/getting-started/no-auth/) for what's
in that state.

That's it. No `NOOK_API_KEY`, no browser login, nothing to configure. Next: run your first real
search in the [quickstart](/getting-started/quickstart/).
