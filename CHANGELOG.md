# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

First public release of `nook` — an agent-first, **read-only** Airbnb search + availability CLI.
Born pinned to **Agent CLI Guidelines v0.4.0, Full**. Booking is deliberately out of scope.

### Added
- `search <location>` — listing discovery with full filter set (dates, guests, price, room-type,
  bedrooms/beds/baths, amenities, superhost, bbox/lat-lng), cursor-paginated and token-bounded.
- `availability <id>` — **the wedge:** a forward per-day calendar (`--months 1..12` or
  `--start/--end`), month-batched: available / checkin / checkout / min-nights / price per day. No
  free competitor offers it.
- `place search <query>` — resolve a location string to `{placeId, coordinates, bbox}` so `search`
  is deterministic.
- `listing get <id>` — full listing details; free text fenced untrusted.
- `reviews <id>` — recent reviews, fenced untrusted, bounded/paginated.
- `doctor` — connectivity, TLS-impersonation availability, key/hash cache freshness, and
  throttle + circuit-breaker state; surfaces the legitimacy notice.
- `schema --json` self-description (command tree, flags, exit codes, live safety state, and a
  machine-readable conformance block), `agent` (embedded SKILL.md), and `version --check`
  (structured, fail-silent update awareness — never auto-updates).
- **Agent-CLI contract:** stable versioned JSON envelope (`schemaVersion`) carrying an explicit
  `scope` (`{auth: none, corpus: public-logged-out}`), `--format json|plain|tsv`,
  `--select`/`--limit`/`--cursor` token bounding, structured errors with remediation.
- **Zero-auth access:** self-healing scrape + TTL cache of Airbnb's own **public** API key and the
  rotating `StaysSearch` / `PdpAvailabilityCalendar` persisted-query hashes.
- **Backend etiquette:** `curl_cffi` TLS/JA3 impersonation of the real Chrome client, a persistent
  **cross-process** politeness throttle, and a circuit breaker that fails fast on a block (exit `7`,
  `--wait` to opt into blocking). No proxies / IP rotation / CAPTCHA solving — *reduce volume, never
  disguise identity.*
- Semantic exit codes including **`20 UPSTREAM_DRIFT`** (public key/hash scrape or response shape
  broke — distinct from a throttle/block) and `7` (rate limited / blocked).
- **Prompt-injection hardening:** third-party Airbnb text (descriptions, host bios, house rules,
  review text, host-authored titles/badges) sanitized and fenced as untrusted by default in agent
  mode.

### Security
- `version --check` only honors a `NOOK_RELEASES_URL` override over `https` (any host) or `http` to
  localhost, ignoring any other scheme/host — so the override can't be used for SSRF or local-file
  reads. `nook` stores **no user secrets**; local state holds only the public key + throttle state.

[Unreleased]: https://github.com/rnwolfe/nook/commits/main
