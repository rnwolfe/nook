# Support

Need help with `nook`?

1. **Built-in self-help** — fastest:
   - `nook --help` / `nook <command> --help` — example-led help.
   - `nook doctor --json` — checks connectivity, TLS-impersonation, key/hash cache freshness, and
     throttle + circuit-breaker state.
   - `nook agent` — the full usage contract (and legitimacy boundary) embedded in the binary.
   - `nook schema --json` — command tree, flags, exit codes, live safety state.
2. **Docs** — see the README and the documentation site.
3. **Questions / ideas** — open a [GitHub Discussion](https://github.com/rnwolfe/nook/discussions).
4. **Bugs** — open an [issue](https://github.com/rnwolfe/nook/issues/new/choose) (the form asks for
   `nook version`, OS/Python, repro, and the `--json` output / structured error).
5. **Security** — do **not** use public issues; see [SECURITY.md](SECURITY.md).

**Common gotchas**

- Getting exit `7` (rate limited / blocked)? The Airbnb backend is reverse-engineered — the circuit
  breaker has tripped. Back off (the error tells you when it clears), or pass `--wait` to block until
  it does. **Do not** retry into a block; `nook` will not, and neither should you.
- Getting exit `20` (`UPSTREAM_DRIFT`)? Airbnb likely changed its public key, persisted-query hash,
  or response shape — the tool needs an update, not a back-off. Check for a newer release
  (`nook version --check`) or file a bug.
- `availability` slow? It's month-batched — request a smaller `--months` window.

This is a community project maintained on a best-effort basis. No SLA.
