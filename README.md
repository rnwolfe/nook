# nook

**Agent-friendly Airbnb search + availability — read-only, JSON-first. Booking excluded by design.**

[![CI](https://github.com/rnwolfe/nook/actions/workflows/ci.yml/badge.svg)](https://github.com/rnwolfe/nook/actions/workflows/ci.yml)
[![Release](https://github.com/rnwolfe/nook/actions/workflows/release.yml/badge.svg)](https://github.com/rnwolfe/nook/actions/workflows/release.yml)
[![PyPI](https://img.shields.io/pypi/v/nook)](https://pypi.org/project/nook/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Agent CLI Guidelines: Full](https://aclig.dev/badge/agent-cli-guidelines-full.svg)](https://aclig.dev/conformance/)

`nook` gives an AI agent (or you) clean, bounded JSON for Airbnb **listing search/discovery**,
**listing details**, and a **forward availability calendar** (per-day available / min-nights /
price) — the piece other tools don't give you for free. It never books, never logs in, and reads
only public, logged-out data.

> Conforms to the [Agent CLI Guidelines](https://aclig.dev) at **v0.4.0** · read-only · MIT.

<p align="center">
  <img src="demo/nook.gif" alt="nook demo — real Airbnb search in Lisbon, the forward availability-calendar wedge (open nights + min-nights), listing details, and its read-only / no-auth conformance" width="900">
</p>

## Quickstart
```bash
uvx nook search "Lisbon" --checkin 2026-08-01 --checkout 2026-08-05 --guests 2 --json
uvx nook availability 12345678 --months 3 --json
uvx nook listing get 12345678 --json
```
Install for repeated / agent use:
```bash
uv tool install nook      # then call the bare `nook`
```

## Commands
| Command | What |
|---|---|
| `nook search <location>` | Search listings (dates, price, guests, room-type, amenities, bbox…). |
| `nook place search <query>` | Resolve a location string → `{placeId, coordinates, bbox}`. |
| `nook listing get <id>` | Full details for one listing. |
| `nook availability <id>` | Forward per-day calendar (`--months 1..12` or `--start/--end`). |
| `nook reviews <id>` | Recent reviews (free text fenced untrusted). |
| `nook doctor` · `schema` · `agent` · `version --check` | Health, machine schema, embedded guide, update check. |

## Safety, etiquette & legitimacy
`nook` is **read-only** (mutation flags are inert), **fences untrusted text** by default, and is a
polite guest: it self-throttles with cross-process state and **circuit-breaks on a block** rather
than retrying into it. It presents the real web client's fingerprint and Airbnb's own public key at
low volume — **no proxies, no IP rotation, no CAPTCHA solving. Reduce volume, don't disguise
identity.**

It reads *publicly visible, logged-out* pages at *personal, single-user scale*. Airbnb's ToS
prohibit automated access (a contract term) and `robots.txt` disallows search paths / asks AI
agents off `/rooms/`; accessing public pages is generally not a computer-crime in the US
(*Van Buren* 2021; *hiQ* 2022; *Meta v. Bright Data* 2024). Expect breakage; use at your discretion.
Not legal advice. See `nook agent` for the full boundary.

## Status
Scaffolded (contract surface + tests green). The real Airbnb client is wired by `cli-implement`.
