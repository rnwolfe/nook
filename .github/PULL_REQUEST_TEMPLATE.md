<!-- Title must follow Conventional Commits, e.g. `feat: add --amenities filter` -->

## What & why

<!-- What does this change and why? Link any issue: Closes #123 -->

## Checklist

- [ ] Title uses [Conventional Commits](https://www.conventionalcommits.org/) (`feat:` / `fix:` / `docs:` / …)
- [ ] `uv run pytest -q` passes locally
- [ ] Output contract respected: **append-only** fields; stdout=data / stderr=chatter
- [ ] If the agent-facing surface changed: `schemaVersion` bumped + schema snapshot (`tests/test_cli.py`) updated
- [ ] **Read-only invariant preserved** (no new mutations; booking stays out of scope)
- [ ] Backend etiquette intact (self-throttle, circuit-break, no evasion)
- [ ] `CHANGELOG.md` (Unreleased) and docs / `src/nook/SKILL.md` updated if behavior changed
- [ ] Agent-CLI contract not regressed (stable JSON, structured errors, semantic exit codes, bounded output)
- [ ] Commits signed off (`git commit -s`, DCO)
