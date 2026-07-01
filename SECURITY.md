# Security Policy

## Supported versions

`nook` is pre-1.0; only the latest released version receives security fixes.

| Version | Supported |
|---------|-----------|
| latest `0.x` | ✅ |
| older | ❌ |

## Reporting a vulnerability

**Please do not open a public issue for security problems.**

Use **GitHub Private Vulnerability Reporting** (the repo's *Security → Report a vulnerability*
tab), or email **rn.wolfe@gmail.com** with `nook security` in the subject.

- **Acknowledgement:** within ~48 hours.
- **Disclosure:** coordinated. We'll agree on a timeline and credit you (opt-in) in the release notes.
- **Safe harbor:** good-faith research that respects others' privacy/data and avoids service
  disruption will not be pursued. Include a minimal reproducible PoC and the `nook version` output.

## Threat model

`nook` is a **read-only**, **no-auth** tool. It never logs in, never books, and stores **no user
secrets or credentials** — there is no login, no OAuth token, no API key of yours, and no cookie
jar. The classic credential-handling attack surface (at-rest secret storage, argv/`ps` leakage,
keyring fallback) therefore **does not apply**. The relevant surface is narrower:

| Threat | Mitigation |
|---|---|
| **SSRF / local-file read via the update check** | `nook version --check` will follow a `NOOK_RELEASES_URL` override **only** over `https://` (any host) or `http://` to `localhost`/`127.0.0.1`/`::1` (for tests). A hostile value (`file://…`, `http://169.254.169.254/…`, other schemes/hosts) is **ignored** and the check falls back to the default endpoint — the override can't be turned into an SSRF or local-file read. Enforced by `_safe_release_url()` and pinned by `tests/test_cli.py::test_version_check_rejects_unsafe_scheme`. |
| **Prompt injection via third-party Airbnb text** | Free text from the upstream (listing descriptions, host bios, house rules, review text, host-authored titles/badges) is **fenced/sanitized as untrusted by default in agent mode** (`--wrap-untrusted`): treated as data, not instructions. Un-fencing requires an explicit `--no-wrap` on the human path. |
| **Upstream tampering / breakage** | The reverse-engineered GraphQL backend is treated as untrusted. A failed public-key/persisted-hash re-scrape or a changed response shape becomes `UPSTREAM_DRIFT` (exit `20`) — distinct from a throttle/block (exit `7`) — never silent wrong data. |
| **Backend etiquette / legitimacy** | `nook` presents the *real web client's* TLS profile and Airbnb's own *public* key at low volume. It performs **no evasion**: no proxy/IP rotation, no residential proxies, no CAPTCHA solving, no UA rotation, no session replay to reach gated data. On a block it **circuit-breaks and stops** (exit `7`) rather than retrying into it. The rule is *reduce volume, never disguise identity*; if Airbnb blocks it, the correct response is to stop, not to evade. |

### Local state

`$XDG_STATE_HOME/nook/` (typically `~/.local/state/nook/`) holds only **non-secret** data:

- Airbnb's **public** `X-Airbnb-Api-Key` (the same key Airbnb ships to every anonymous visitor) and
  the rotating `StaysSearch` / `PdpAvailabilityCalendar` persisted-query hashes, scraped live and
  cached with a TTL.
- Throttle token-bucket / last-request timestamps and circuit-breaker state (`tripped_until`).

None of this is a user credential; deleting the directory is always safe (it re-bootstraps on the
next call).
