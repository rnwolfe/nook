# spec.md — nook

> The build spec for an agent-focused CLI. Written by `cli-plan`; consumed by `cli-scaffold`,
> `cli-implement`, and `cli-publish`. Keep it current — it is the single source of truth.
>
> **Name:** `nook` (a cozy spot to stay). Alternates if it collides at publish: `perch`, `roost`.
> Booking is deliberately **out of scope** — this tool discovers listings and checks availability;
> booking (the only real mutation) would ever be a separate tool.
> **Born pinned to Agent CLI Guidelines `spec.current` = 0.4.0.**

## Target
- **Service**: Airbnb — public, logged-out listing **search/discovery** + forward **availability**.
- **Surface**: undocumented web **GraphQL** API (`/api/v3/`), the same endpoints Airbnb's own SPA
  calls. Confirmed live via `johnbalvin/pyairbnb` v2.2.1 (Feb 2026):
  - `POST /api/v3/StaysSearch/{sha256Hash}` — map/bbox listing search
  - `GET  /api/v3/PdpAvailabilityCalendar/{sha256Hash}` — per-day availability (up to 12 months)
  - `StaysPdpSections` — full listing details; `api/v2/autocompletes-personalized` — place resolve
  - Auth key: `X-Airbnb-Api-Key`, a **public static key Airbnb ships to every anonymous visitor**
    (historically `d306zoyjsyarp7ifhu67rjxn52tv0t20`). **Scrape it live** from homepage HTML
    (`"api_config":{"key":"…"`) rather than hardcoding — survives rotation.
  - `StaysSearch`'s persisted-query **hash rotates** → fetch live from the JS bundle with a
    hardcoded fallback. `PdpAvailabilityCalendar`'s hash has been stable. **This is the one real
    maintenance burden.**
- **Rate limits / pagination**: no published numbers; adaptive. Community signal: single-digit
  requests at human pacing are fine; ~20–30 rapid requests/IP draw `429`/challenges; **datacenter
  IPs are blocked pre-app-layer**. Search paginates via cursor (`StaysSearch` offset/cursor); the
  calendar is month-batched. **An agent spawns a fresh process per call → throttle/circuit-breaker
  state MUST persist cross-process (`$XDG_STATE_HOME/nook/`); an in-memory timer is a no-op.**
- **ToS / risk (state loudly)**: **unofficial/scraped.** Airbnb ToS prohibit automated access
  (help/article/2908) — a **contract** term, not (for logged-out public data) a crime
  (*Van Buren* 2021; *hiQ* 9th Cir. 2022; *Meta v. Bright Data* N.D. Cal. Jan 2024 — ToS bind only
  logged-in users). `robots.txt` disallows `/s/*/*` search paths and asks **AI-named agents off
  `/rooms/` entirely**. Expect breakage when Airbnb reshapes pages/hashes. **No credential
  sensitivity** — no login, no user secrets. The legitimacy boundary is disclosed in README +
  `agent` output (full text in §Legitimacy below).
- **Prior art / competitive landscape** (all verified 2026-07-01):
  - **`openbnb-org/mcp-server-airbnb`** (MCP, 481★, maintained) — `airbnb_search` + `listing_details`
    only. **No availability calendar.** SSR HTML scrape. Strong bounded output. Gap: no calendar,
    ad-hoc errors, no exit codes, brittle DOM parse.
  - **`pp-airbnb`** (CLI Printing Press, Go, ~3.8k★ engine, agent-first) — search/get + compound cmds.
    **No forward availability-calendar dump.** SSR HTML scrape (brittle). Cookie-to-disk auth, no
    keyring. *Strategic note: the whole "CLI Printing Press" is a rival to the agent-cli-factory —
    worth watching beyond this entry.*
  - **`johnbalvin/pyairbnb`** (Python lib, the only maintained one, v2.2.1 Feb 2026) — the one prior
    art with a real `get_calendar`; GraphQL persisted-query + self-healing key/hash via `curl_cffi`.
    **Mine this for access mechanics.** It's a library, not an agent CLI.
  - Paid Apify actors (`rigelbytes/airbnb-availability-calendar`) are the only other calendar source —
    closed, $10/mo + residential proxies, tiny adoption.
- **Build verdict**: **BUILD.** Search/details alone would be *redundant* (openbnb + pp-airbnb cover
  it), but a **free, local, agent-grade forward availability calendar** is a genuine open gap — the
  exact "availability checking" the operator asked for. Differentiators:
  1. **`availability` as a first-class command** — token-bounded forward per-day calendar
     (available / checkin / checkout / min-nights / price). No free competitor offers it.
  2. **GraphQL persisted-query access with self-healing key+hash** (mine `pyairbnb`) — resilient
     where openbnb/pp-airbnb's DOM scraping rots on every Airbnb redesign.
  3. **The full agent contract the incumbents miss** — documented exit codes **and** typed structured
     errors, a distinct `UPSTREAM_DRIFT` code, `schema --json` self-description, cross-process
     circuit-breaker/throttle, prompt-injection fencing.
  4. **Token-aware bounded output by default** — cursor pagination + `--select` projection + hard
     result caps tuned so one search never blows an agent's context.
  Mine for mechanics: **`johnbalvin/pyairbnb`** (key/hash extraction, `StaysSearch`,
  `PdpAvailabilityCalendar`).

## Language & framework
- **Language**: **Python.**
- **Rationale (SDK gravity > distribution > performance)**: the only maintained access library
  (`pyairbnb`) and the linchpin TLS-impersonation lib (`curl_cffi`) are both Python; fleet precedent
  is `gfly` (also scraped travel, Python/uvx). SDK gravity is decisive.
- **Framework**: **Click 8.4+** (built-in `to_info_dict` → `schema --json`; 8.4 did-you-mean;
  8.2 split stdout/stderr). Plain Click, not Typer.
- **SDK/library used**: **direct HTTP via `curl_cffi`** (`impersonate="chrome"`) — a deliberate
  deviation from the blueprint's default `httpx`, because **TLS/JA3 must match a real Chrome or every
  call `403`s at the TLS layer** (this is the operator-ratified "act like the real client" boundary,
  see §12). Port `pyairbnb`'s GraphQL + self-healing key/hash logic rather than depending on the lib
  (keeps our contract surface + error taxonomy clean). `keyring>=24` present but **unused** (no user
  secrets).
- **Blueprint**: references/research/blueprint-python.md
- **Language-specific gotchas to honor**: `curl_cffi` has a native component but ships prebuilt
  wheels (fine for uv; accept a slightly heavier install than pure-Python). Cold-start is acceptable
  for this I/O-bound tool. src layout, PEP 621, `uv_build`, syrupy JSON snapshot test as the CI schema
  gate.

## Auth
- **Model**: **none.** Public, logged-out access with the site's own public `X-Airbnb-Api-Key`
  (scraped live). No OAuth, no login, no user token, no cookies for search/availability.
- **Provider constraints**: n/a (no auth). The only "credential" is the public API key + the rotating
  persisted-query hash, both **scraped live and cached** in `$XDG_STATE_HOME/nook/` with a TTL and
  self-healing re-scrape.
- **Feasible path to usability (end-to-end)**: `nook search "Lisbon" --checkin … --checkout …`
  works **with zero setup** — the tool bootstraps the public key + hash on first call and caches them.
  There is no auth step for an agent to complete because none is required. (Contract §7 "never
  browser-only as sole path" is satisfied vacuously — there is no auth path at all.)
- **Secret storage**: n/a — no user secrets. `keyring` dep retained for contract uniformity only.
- **Subcommands**: **no `auth *`.** Replaced by **`doctor`** (connectivity, TLS-impersonation
  availability, key/hash cache freshness, throttle + circuit-breaker state).
- **Scope declaration (§1)**: every envelope carries
  `"scope": {"auth": "none", "corpus": "public-logged-out"}` so an agent never mistakes the
  logged-out public view for a complete/authenticated one.

## Command surface (noun-verb)
| Command | Read/Mutation | Description | Key output fields |
|---|---|---|---|
| `nook search <location>` | read | Search listings (discovery). Filters below. Cursor-paginated, bounded. | `id, name, roomType, price{amount,currency,qualifier}, rating, reviewsCount, coordinates{lat,lng}, badges[], superhost, url` |
| `nook place search <query>` | read | Resolve a location string → place candidates (autocomplete) so `search` is deterministic. | `placeId, name, type, coordinates{lat,lng}, bbox{ne,sw}` |
| `nook listing get <id>` | read | Full listing details. Free-text **fenced**. | `id, name, description*, host{id,name,isSuperhost}, roomType, capacity{guests,bedrooms,beds,baths}, amenities[], houseRules*, location{lat,lng,city}, rating{overall,breakdown}, reviewsCount, photos[], price, cancellationPolicy, url` |
| `nook availability <id>` | read | **The wedge.** Forward per-day calendar; `--months 1..12` (default 1) or `--start/--end`. Month-batched. | `date, available, availableForCheckin, availableForCheckout, bookable, minNights, maxNights, price{amount,currency}` |
| `nook reviews <id>` | read (secondary) | Recent reviews, **fenced**, bounded/paginated. | `id, date, rating, language, text*, reviewer{firstName}` |
| `nook doctor` | read | Health: connectivity, TLS-impersonation present, key/hash cache freshness, throttle + breaker state, legitimacy notice. | `checks[]{name,ok,detail}, keyAgeS, hashAgeS, breaker{tripped,until}` |
| `nook schema --json` | read | Full command tree + flags + exit codes + live safety state + `conformance` block. | (contract-standard) |
| `nook agent` | read | Print embedded SKILL.md (usage + legitimacy boundary) to stdout. | (text) |
| `nook version --check` | read | `{current, latest, updateAvailable, upgrade}` — fail-silent, human-only passive notice. | (contract-standard) |

`*` = free text from Airbnb → **wrapped untrusted by default in agent mode** (§Prompt-injection).

**Search filters** (all optional): `--checkin --checkout --guests --adults --children --infants --pets
--min-price --max-price --room-type {entire,private,shared,hotel} --bedrooms --beds --bathrooms
--amenities a,b,c --superhost --place-id --lat --lng --bbox --currency --limit --cursor --sort`.

**Read/mutation split:** **100% read-only.** No command mutates Airbnb state. `--allow-mutations`
exists for contract uniformity but is structurally unreachable (there is no mutation to gate) — this
is stated in `schema` and `agent`. Booking (the only real mutation) is explicitly out of scope.

## Exit codes
Start from contract §4; target-specific addition is **`20 UPSTREAM_DRIFT`**.
```
0   ok
1   generic error
2   usage / parse
3   empty results        (search / calendar returned nothing)
5   not found            (listing id invalid or removed)
7   rate limited/blocked (circuit-break: 403 challenge / 429 / "Press & Hold" CAPTCHA — do NOT retry into it)
8   retryable/transient  (network, 5xx)
10  config error
13  input required       (--no-input hit a prompt)
20  upstream drift       (target-specific: public key/persisted-hash scrape failed, or response shape
                          changed — tool likely needs an update; DISTINCT from a transient block so an
                          agent can tell "Airbnb changed" from "I'm being throttled")
130 cancelled (SIGINT)
```
Present-but-unreachable (kept for contract uniformity, documented as N/A): `4 auth required`,
`6 permission denied`, `12 mutation blocked` (no auth, no mutations).

## Output schema
Stable, append-only. Every response is an envelope:
```json
{
  "schemaVersion": 1,
  "scope": { "auth": "none", "corpus": "public-logged-out" },
  "data": <command payload>,
  "nextCursor": "<opaque|null>",
  "meta": { "count": <int>, "truncated": <bool>, "currency": "<iso>" }
}
```
- **search.data**: `[ {id,name,roomType,price{amount,currency,qualifier},rating,reviewsCount,
  coordinates{lat,lng},badges,superhost,url} ]`
- **place.data**: `[ {placeId,name,type,coordinates{lat,lng},bbox{ne{lat,lng},sw{lat,lng}}} ]`
- **listing.data**: full object (table above); free-text fields fenced.
- **availability.data**: `[ {date,available,availableForCheckin,availableForCheckout,bookable,
  minNights,maxNights,price{amount,currency}} ]` (one entry per day).
- **reviews.data**: `[ {id,date,rating,language,text,reviewer{firstName}} ]`
- Errors (§3): `{ "error": <msg>, "code": <STABLE_STRING>, "remediation": <next step> }` to stderr.

## Universal contract surface (provided by scaffold — confirm no conflicts)
`--format json|plain|tsv` · `--allow-mutations` (present, unreachable) · `--dry-run` · `--yes`/`--force`
· `--no-input` · `--limit` · `--select` · `--concise`/`--detailed` · `schema --json` · `agent`.
No conflicts. Because the tool is 100% read-only, `--dry-run`/`--yes`/`--force` are no-ops documented
as such.

## Backend etiquette — §12 (LOAD-BEARING; unofficial/scraped target)
- **HTTP**: `curl_cffi` `impersonate="chrome"` with a single genuine desktop-Chrome UA that MATCHES
  the impersonation. **No proxies, no proxy/IP rotation, no residential proxies, no CAPTCHA solving,
  no UA rotation.** The only anti-bot-adjacent step is presenting the *real web client's* TLS profile
  + its *public* key — the operator-ratified boundary (2026-07-01): *reduce volume, don't disguise
  identity.*
- **Cross-process persistent state** in `$XDG_STATE_HOME/nook/` (`~/.local/state/nook/`):
  (a) cached public API key + `StaysSearch`/`PdpAvailabilityCalendar` persisted hashes (TTL +
  self-healing re-scrape → `UPSTREAM_DRIFT` if re-scrape fails); (b) throttle token-bucket /
  last-request timestamps; (c) circuit-breaker state (`tripped_until`).
- **Self-throttle**: conservative default (~1 req/s, max concurrency 1, jittered); honor
  `Retry-After`; exponential backoff on `8`.
- **Circuit-break**: on 403-challenge / 429 / "Press & Hold" → trip breaker, **exit `7`, do NOT retry
  into it**. **Fail fast** by default (a hung CLI deadlocks the agent); `--wait` opt-in to block until
  the breaker clears.
- **Legitimacy boundary** disclosed in README + `agent` output + surfaced by `doctor` (§Legitimacy).

## Prompt-injection surface (§8)
Commands returning free text from Airbnb → **wrap as untrusted by default in agent mode**
(`--wrap-untrusted`, default-ON for agents): `listing get` (description, host bio, house rules),
`reviews` (review text), and listing **titles/badges** in `search` (host-authored). Fencing is
stripped only under an explicit `--no-wrap` on the human path.

## Legitimacy boundary (drop-in for README + `agent` output)
> **Legitimacy boundary.** `nook` reads *publicly visible, logged-out* Airbnb search and listing
> pages at *personal, single-user scale* — a handful of queries for your own trip planning, at
> human-like pacing, read-only. It never books, never transacts, never logs in.
>
> **Defensible:** US courts treat accessing public pages as generally not a CFAA violation
> (*Van Buren* 2021; *hiQ* 9th Cir. 2022) and hold that Terms don't bind *logged-out* access
> (*Meta v. Bright Data* N.D. Cal. 2024). Low-volume, logged-out, read-only sits at the safe end.
>
> **The risk you accept:** Airbnb's ToS say *"Do not use bots, crawlers, scrapers, or other automated
> means to access or collect data … from … the Airbnb Platform"* — a contract term (how *hiQ*
> ultimately lost to LinkedIn). `robots.txt` disallows search paths and asks AI agents off `/rooms/`.
> Airbnb can rate-limit, block, or change page structure anytime — expect breakage.
>
> **Hard rule — reduce volume, never disguise it.** No CAPTCHA solving, no proxy/IP rotation, no
> residential proxies, no session replay to reach gated data. `nook` makes *fewer, slower, honest*
> requests than a person clicking around; it does not hide who is asking. If Airbnb blocks it, the
> correct response is to stop, not to evade.
>
> *Not legal advice.*

## Distribution
- **Targets**: **PyPI** via `uv build` + `uv publish` (Trusted Publishing / OIDC — a human-only
  prerequisite). Homebrew tap optional/later (like `gfly`).
- **Trial path (humans)**: `uvx nook search "Lisbon" --checkin 2026-08-01 --checkout 2026-08-05`.
- **Agent hot-loop path**: `uv tool install nook` → call bare `nook` (no per-call resolution).

## Publish
- **Flag**: **full** (portfolio-bound).
- **License**: **MIT** (single `LICENSE`).
- **If full**: docs site (starlight-docs) · doc content (harvest-docs) · release (tag-driven OIDC
  workflow / `release` skill) · README + VHS demo · hygiene files · discoverability targets.
  - **Web presence**: bold custom landing page + Starlight docs sharing **ONE design-token source**;
    per-page **OG/social cards**; a 1280×640 social preview.
  - **Deploy target**: **Vercel** (custom domain, git-connected auto-deploy), CI.
  - **Custom domain (candidate)**: **`nook.sh`** (fallbacks `trynook.sh`, `nookcli.sh`) — publish
    confirms availability via the Vercel domain tool; operator buys. If `nook` collides, fall back to
    `perch`/`roost` and re-derive the domain. Until bought+bound: `domain: null` + `planned_domain`.
  - **Canonical docs URL**: `https://docs.nook.sh` (serves `/llms.txt`); `nook.sh` is the landing.
    Both asserted only once wired.
- **Gated (do NOT add until flag true)**: `.github/FUNDING.yml` / Sponsor — only if
  `discoverability.yaml → funding.sponsors_live: true`.

## Open follow-up (not blocking this build)
- The TLS-impersonation boundary decision may warrant a **one-line §12 clarification** in the Agent
  CLI Guidelines ("matching the genuine web client's TLS profile + its public key is not evasion;
  forging/rotating identities or defeating challenges is"). Route via **`spec-propose → spec-ratify`**,
  separate from this build. `nook` ships conformant to 0.4.0 as-is.
