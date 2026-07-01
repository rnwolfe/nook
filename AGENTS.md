# AGENTS.md — nook

Agent-friendly Airbnb search + availability CLI (read-only; booking excluded). Python / Click,
uv toolchain. Conforms to the [Agent CLI Guidelines](https://aclig.dev) at **v0.4.0**
(profile in the factory's `contract.md`).

## Build / test / run
```bash
uv sync --extra dev              # install deps (incl. curl_cffi, pytest)
uv run pytest -q                 # contract tests must stay green
uv run nook schema --json        # inspect the machine surface
uv run nook search "Lisbon" --json
```

## Conventions
- **stdout = data, stderr = everything else.** Never print notes/progress to stdout.
- **Read-only.** No command mutates Airbnb state. The mutation gate (`Runtime.guard`,
  `--allow-mutations`, `--dry-run`) is present for contract uniformity but inert — do not wire a
  real mutation without routing scope through `cli-plan`/`spec.md` first.
- **Output is an append-only contract.** Field names in `output.py` envelopes + `client.py` return
  shapes are stable; a rename/removal is a reviewed diff (schema-snapshot CI gate), not a silent
  break. See `spec.md §Output schema`.
- **Untrusted text is fenced** (contract §8): listing descriptions, host bios, house rules, review
  text. Keep the fencing default-ON in agent mode.
- **Backend etiquette (contract §12) is load-bearing:** `client.py` must self-throttle with
  **cross-process** state (`$XDG_STATE_HOME/nook/` — an agent spawns a fresh process per call),
  circuit-break on a block (exit 7, do not retry into it), and **never evade** (no proxies/IP
  rotation/CAPTCHA solving). TLS/JA3 impersonation via `curl_cffi` is the ratified boundary: match
  the real web client, don't disguise identity.
- **`UPSTREAM_DRIFT` (exit 20)** is distinct from a rate limit — raise it when the public API key /
  persisted-query hash scrape or the response shape breaks, so an agent knows the tool needs an
  update rather than a back-off.

## Freshness directive (commit-coupled)
When you change the command surface, flags, output schema, exit codes, or the safety/etiquette
posture, in the SAME change update: the embedded **`src/nook/SKILL.md`**, **`README.md`**, the
**docs site** (pages + `llms.txt`), the **landing page** copy, and the **OG/social cards** if the
positioning changed. `schema --json` is generated from the parser and cannot drift; the prose
artifacts can — keep them in lockstep. Bump the conformance version only via `spec-rollout`.

## Web presence (`site/` — Astro + Starlight)

The site lives in `site/` and is the "vacancy board" theme: warm espresso canvas, cream text,
terracotta/amber accents, Fraunces display. **One shared token source** —
`site/src/styles/tokens.css` (the `--nk-*` custom properties) — styles BOTH the landing
(`site/src/pages/index.astro`) and the docs (via `customCss` in `site/astro.config.mjs`). Never
hand-copy tokens. Package manager is **pnpm**.

When the value proposition, command surface, flags, exit codes, or brand change, in the SAME PR:
1. Update the affected docs page under `site/src/content/docs/` (Diátaxis IA; pages are currently
   **stubs pending a `harvest-docs` pass** — written from `README.md` + `src/nook/SKILL.md`).
2. Update the **landing** copy/examples in `site/src/pages/index.astro` (hero calendar, the
   "hard way vs nook way" beats, the wedge/legitimacy sections).
3. **Regenerate OG cards** if any page title/headline changed: `cd site && node scripts/gen-og.mjs`
   (keep the page list there and the `known` list in `src/components/Head.astro` in sync). If the
   brand/tagline/headline changed, also regenerate the GitHub social card:
   `cd site && node scripts/gen-social.mjs` → `public/social-card.png` + `.github/social-preview.png`
   (re-upload in repo Settings → Social preview). Cards need headless Chrome (`CHROME_BIN`) + sharp.
4. Rebuild (`cd site && pnpm build`) so `llms.txt` regenerates.

Build/preview: `cd site && pnpm install && pnpm build` / `pnpm dev` (binds `0.0.0.0`). Deploy is
NOT set up. Planned domain **nookcli.sh** (docs at docs.nookcli.sh) is not yet bought/bound — only
`astro.config.mjs`'s `site:` references it, for canonical/OG URLs.

## Layout
- `src/nook/cli.py` — Click command tree, runtime, exit-code mapping (contract surface; stable).
- `src/nook/output.py` — envelope + stdout/stderr split + `--select`/`--limit` (stable).
- `src/nook/errors.py` — exit-code table + `AppError` (stable).
- `src/nook/client.py` — **the Airbnb client** (placeholder until cli-implement; the real GraphQL +
  curl_cffi + throttle/breaker lives here).
- `src/nook/skill.py` — loads the embedded `SKILL.md` for `nook agent`.
