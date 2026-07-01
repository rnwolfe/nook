# Contributing to nook

Thanks for helping! `nook` is an agent-first, **read-only** Airbnb search + availability CLI
(booking is deliberately out of scope). `spec.md` is the source of truth for what it is; the
**agent-CLI contract** (read-only, stable JSON, structured errors, bounded output, polite backend
etiquette) is non-negotiable — keep it intact.

## Setup

```bash
uv sync --extra dev          # Python >= 3.10, uv-managed (installs curl_cffi + pytest)
uv run pytest -q             # tests must stay green
uv run nook schema --json    # machine-readable command tree
```

## Develop

- **Layout:** `src/nook/cli.py` (Click grammar + runtime + exit-code mapping), `client.py` (the
  Airbnb GraphQL client), `transport.py` (curl_cffi TLS impersonation), `keyhash.py` (self-healing
  public key + persisted-query hash), `throttle.py` + `state.py` (persistent politeness / circuit
  breaker), `fence.py` (untrusted-text fencing), `output.py` (output discipline — don't break
  stdout=data/stderr=chatter), `errors.py` (exit-code table). See `AGENTS.md`.
- **Heavy imports stay lazy** (inside the functions that use them) so `--help`/`schema` stay fast.
- **Read-only:** no command may mutate remote state. **Do not add mutations without a spec change** —
  route it through `spec.md` first. Booking is out of scope by design; it would be a separate tool.
- **Output contract is append-only:** add fields freely; never rename/remove. A breaking shape
  change means bumping `schemaVersion` and updating the schema snapshot in the same PR.
- **Backend etiquette is load-bearing** (`spec.md §12`): self-throttle with **cross-process** state,
  circuit-break on a block (exit `7`, don't retry into it), and **never evade** (no proxies / IP
  rotation / CAPTCHA solving / UA rotation). Matching the real web client's TLS profile via
  `curl_cffi` is the ratified boundary — *reduce volume, don't disguise identity*.
- **`UPSTREAM_DRIFT` (exit 20)** is distinct from a rate limit — raise it when the public key /
  persisted-hash scrape or the response shape breaks, so an agent knows the tool needs an update
  rather than a back-off.

## Tests

```bash
uv run pytest -q
```

Network is mocked in tests. The **schema / command-surface snapshot is the CI gate**
(`tests/test_cli.py::test_schema_command_surface_snapshot`) — if it fails, you changed the
agent-facing contract; make that a deliberate, reviewed diff. **Don't regress the agent-CLI
contract**: stable JSON envelope, structured errors, semantic exit codes, bounded output.

## Pull requests

- Use **[Conventional Commits](https://www.conventionalcommits.org/)** (`feat:`, `fix:`, `docs:`,
  `refactor:`, `test:`, `chore:`) — they drive the changelog and semver bump.
- Sign off your commits (**DCO**): `git commit -s`. **No CLA.**
- Keep PRs focused; update `CHANGELOG.md` (Unreleased) and `src/nook/SKILL.md` / docs when behavior
  changes.
- Green CI required: tests + `nook schema` smoke.

## Reporting bugs / security

- Bugs: open an issue (the form asks for `nook version`, OS/Python, repro, and the `--json` output).
- Security: **do not** open a public issue — see [SECURITY.md](SECURITY.md).
