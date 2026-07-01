---
title: version --check
description: Report an available upgrade without ever self-updating.
---

`nook version` prints the current version. `nook version --check` also asks GitHub whether a
newer release exists — and then tells you, and only you, what to do about it. nook never
installs anything on your behalf.

## Plain version

```bash
nook version
```

```json
{
  "version": "0.4.0"
}
```

Note the shape: this is a raw JSON object, not the [read envelope](/concepts/output-envelope/).
`version` (with or without `--check`) is a meta command like `schema`, `agent`, and `doctor` —
there's no `scope`, `schemaVersion`, `data`, `nextCursor`, or `meta` wrapper here, and `--select`
projects against this object directly.

## Checking for an upgrade

```bash
nook version --check
```

```json
{
  "current": "0.4.0",
  "latest": "0.5.0",
  "updateAvailable": true,
  "upgrade": "uv tool install --upgrade nook"
}
```

Fields:

- **`current`** — your installed `__version__`.
- **`latest`** — the newest tag nook could find (usually the GitHub Releases API `tag_name`),
  or `null` if the check failed.
- **`updateAvailable`** — `true` only when `latest` is present, `current` is present, `current`
  isn't `"dev"`, and the two version strings differ (leading `v` stripped from each before
  comparing). This is a straight string inequality, not a semver ordering check — it answers
  "is there a different release out there," not "is it strictly newer."
- **`upgrade`** — always `"uv tool install --upgrade nook"`. nook reports this command; it never
  runs it.

If the check itself fails, `latest` comes back `null`, `updateAvailable` is `false`, and a
`note: "could not check for updates"` field is added so you know the absence of an update isn't
a green light — it's just silence.

```json
{
  "current": "0.4.0",
  "latest": null,
  "updateAvailable": false,
  "upgrade": "uv tool install --upgrade nook",
  "note": "could not check for updates"
}
```

## nook never self-updates

This is contract §11 (update awareness, never self-mutation), and it's a hard line: `--check`
only *reports*. There is no `nook update`, no auto-download, no background install. The
`upgrade` field is copy-pasteable, nothing more. If you want the new version, you run the
command yourself (or your agent does, deliberately, outside of nook).

## Dev builds don't nag

If nook can't resolve its own installed-package version (e.g. you're running from a source
checkout without an installed distribution), `current` reports as `"dev"`. In that case
`updateAvailable` is always `false` — a dev build never tells you you're behind, because there's
no meaningful version to compare against. This keeps local development quiet instead of
constantly flagging a phantom upgrade.

## Network behavior: short timeout, fail-silent

The check is a single HTTP GET, 3-second timeout, and it swallows every failure — DNS errors,
timeouts, 404s, malformed JSON, rate limiting, anything. There's no retry, no circuit-breaker
interaction (this isn't a search/availability/reviews call against Airbnb, so it doesn't touch
the shared rate limiter), and no non-zero exit code tied to a failed check. Worst case, you get
`"latest": null` and the `note`. `nook version --check` is safe to run in a loop or a CI job
without worrying it'll block or fail your pipeline.

By default nook resolves the release source itself: it scans its own package metadata's
`Project-URL` entries (`Homepage`, `Repository`, etc. — whichever comes first) for one pointing at
`github.com`, extracts the `owner/repo` slug, and asks
`https://api.github.com/repos/<owner>/<repo>/releases/latest`. If no such metadata entry is found
(or you're running a build with no package metadata at all), the check silently no-ops — `latest`
stays `null`.

## `NOOK_RELEASES_URL` and the SSRF guard

You can point the check at a different releases endpoint — useful for testing, forks, or mirrors
— via an environment variable:

```bash
NOOK_RELEASES_URL="https://api.github.com/repos/you/your-fork/releases/latest" nook version --check
```

The override is scheme-guarded before it's ever used:

- **`https://` to any host** — allowed.
- **`http://` to `localhost`, `127.0.0.1`, or `::1`** — allowed (this exists for tests).
- **Everything else is ignored outright** — `http://` to a non-loopback host, `file://`, and
  anything targeting link-local metadata endpoints (e.g. `http://169.254.169.254/...`) all fail
  the guard and nook silently falls back to the default GitHub URL as if the variable weren't
  set.

That guard is the whole point: `NOOK_RELEASES_URL` can't be turned into an SSRF vector or a
local-file read, even if the value comes from an untrusted place (a config file, an
agent-generated environment, etc.). A rejected value never surfaces as an error — it just
doesn't change behavior.

## See also

- [Output envelope](/concepts/output-envelope/) — why `version` output looks different from
  every other command's.
- [Exit codes](/reference/exit-codes/) — `version --check` doesn't map its network failures to
  the same codes as read commands; it just reports `null` + a note.
- [Read-only by design](/concepts/read-only/) — the same posture that makes booking inert makes
  self-updating inert too: nook only ever tells you things, it doesn't act on your behalf.
