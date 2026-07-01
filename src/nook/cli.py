"""nook — agent-friendly Airbnb search + availability CLI (read-only; booking excluded).

kong-equivalent for Python: Click grammar, runtime context, and exit-code mapping. main() does
nothing but sys.exit(run(...)) so every path is testable in-process.

Global flags are attached to every command (not just the root group) so an agent can place them
in any position (e.g. `nook search Lisbon --json`), matching kong's behavior. Values are merged
leaf-first across the context chain.

nook is 100% READ-ONLY: no command mutates Airbnb state. The mutation gate (Runtime.guard,
--allow-mutations, --dry-run, --yes, --force) is present for contract uniformity but no command
calls it — documented as inert in `schema` and `agent`. Booking (the only real mutation) is out
of scope by design."""

from __future__ import annotations

import difflib
import json
import sys
from dataclasses import dataclass

import click

from . import SCOPE, SPEC, __version__
from .client import Client
from .errors import AppError, ExitCode, exit_table, mutation_blocked, not_found
from .fence import fence_fields
from .output import Writer
from .skill import content as skill_content

# Set when a runtime is built, so the top-level error handler knows the chosen format.
_active: "Runtime | None" = None

_GLOBAL_KEYS = ["fmt", "as_json", "no_color", "allow_mutations", "dry_run", "yes", "force",
                "no_input", "limit", "select", "concise", "detailed", "no_wrap"]


def global_options(f):
    """Attach the universal agent-CLI contract flags to a command (tri-state default=None so we
    can tell 'not passed here' from 'passed', and merge across the context chain).

    The mutation flags (--allow-mutations/--dry-run/--yes/--force) are present for contract
    uniformity; nook is read-only, so they are inert no-ops."""
    opts = [
        click.option("--format", "fmt", type=click.Choice(["json", "plain", "tsv"]),
                     default=None, help="Output format: json, plain, or tsv."),
        click.option("--json", "as_json", is_flag=True, default=None, help="Shorthand for --format=json."),
        click.option("--no-color", is_flag=True, default=None, help="Disable colored output."),
        click.option("--allow-mutations", is_flag=True, default=None,
                     help="Present for contract uniformity; no-op (nook is read-only)."),
        click.option("--dry-run", is_flag=True, default=None,
                     help="Present for contract uniformity; no-op (nook is read-only)."),
        click.option("--yes", is_flag=True, default=None,
                     help="Present for contract uniformity; no-op (nook is read-only)."),
        click.option("--force", is_flag=True, default=None,
                     help="Present for contract uniformity; no-op (nook is read-only)."),
        click.option("--no-input", is_flag=True, default=None, help="Never prompt; fail with exit 13."),
        click.option("--limit", type=int, default=None, help="Max items for list results (default 50)."),
        click.option("--select", default=None, help="Comma-separated dot-path field projection."),
        click.option("--concise", is_flag=True, default=None, help="Terser output (default)."),
        click.option("--detailed", is_flag=True, default=None, help="Richer output."),
        click.option("--no-wrap", is_flag=True, default=None,
                     help="Do not fence untrusted Airbnb text (fencing is default-ON in agent mode)."),
    ]
    for o in reversed(opts):
        f = o(f)
    return f


def net_options(f):
    """Extra flags for commands that hit Airbnb: backpressure control (contract §12)."""
    opts = [
        click.option("--wait", is_flag=True, default=False,
                     help="If the circuit-breaker is open, block until it clears (default: fail fast)."),
        click.option("--max-wait", "max_wait", type=float, default=900.0, show_default=True,
                     help="Cap for --wait, in seconds."),
    ]
    for o in reversed(opts):
        f = o(f)
    return f


@dataclass
class Runtime:
    fmt: str
    allow_mutations: bool
    dry_run: bool
    yes: bool
    force: bool
    no_input: bool
    out: Writer
    client: Client
    wrap: bool = True

    def guard(self, op: str) -> None:
        """Mutation gate — kept for contract uniformity. nook wires no mutations, so this is
        never reached in normal operation; the machinery exists (and is unit-tested) so the tool
        is structurally identical to gated members of the fleet."""
        if not self.allow_mutations:
            raise mutation_blocked(op)


def _resolve(ctx) -> dict:
    vals = {k: None for k in _GLOBAL_KEYS}
    c = ctx
    while c is not None:
        for k in _GLOBAL_KEYS:
            if vals[k] is None and c.params.get(k) is not None:
                vals[k] = c.params[k]
        c = c.parent
    return vals


def make_runtime(ctx) -> Runtime:
    global _active
    v = _resolve(ctx)
    fmt = "json" if v["as_json"] else (v["fmt"] or "plain")
    color = (not v["no_color"]) and sys.stdout.isatty() and fmt == "plain"
    sel = [s for s in (v["select"] or "").split(",") if s.strip()]
    limit = v["limit"] if v["limit"] is not None else 50
    out = Writer(fmt=fmt, color=color, limit=limit, select=sel)
    # Fence untrusted text by default for AGENTS (JSON or non-TTY); off on the human plain-TTY
    # path where markers are noise. --no-wrap forces it off regardless (contract §8).
    if v["no_wrap"]:
        wrap = False
    else:
        wrap = (fmt == "json") or (not sys.stdout.isatty())
    _active = Runtime(fmt=fmt, allow_mutations=bool(v["allow_mutations"]), dry_run=bool(v["dry_run"]),
                      yes=bool(v["yes"]), force=bool(v["force"]), no_input=bool(v["no_input"]),
                      out=out, client=Client(), wrap=wrap)
    return _active


class DYMGroup(click.Group):
    """Adds "did you mean" suggestions for unknown subcommands."""

    def resolve_command(self, ctx, args):
        try:
            return super().resolve_command(ctx, args)
        except click.UsageError as exc:
            name = args[0] if args else ""
            matches = difflib.get_close_matches(name, self.list_commands(ctx), n=1)
            if matches:
                exc.message = f"{exc.message}\n  did you mean '{matches[0]}'?"
            raise


@click.group(cls=DYMGroup, context_settings={"help_option_names": ["-h", "--help"]})
@global_options
@click.pass_context
def cli(ctx, **_):
    """Agent-friendly Airbnb search + availability (read-only; booking excluded).

    \b
    Examples:
      nook search "Lisbon" --checkin 2026-08-01 --checkout 2026-08-05 --guests 2 --json
      nook availability 12345678 --months 3 --json
      nook listing get 12345678 --json
      nook place search "Lisbon" --json
    """


# --- search (marquee read command) ------------------------------------------

@cli.command("search")
@click.argument("location")
@click.option("--checkin", help="Check-in date (YYYY-MM-DD).")
@click.option("--checkout", help="Check-out date (YYYY-MM-DD).")
@click.option("--guests", type=int, help="Total guests.")
@click.option("--adults", type=int, help="Adults.")
@click.option("--children", type=int, help="Children.")
@click.option("--infants", type=int, help="Infants.")
@click.option("--pets", type=int, help="Pets.")
@click.option("--min-price", type=int, help="Minimum nightly price.")
@click.option("--max-price", type=int, help="Maximum nightly price.")
@click.option("--room-type", type=click.Choice(["entire", "private", "shared", "hotel"]),
              help="Room type filter.")
@click.option("--bedrooms", type=int, help="Minimum bedrooms.")
@click.option("--beds", type=int, help="Minimum beds.")
@click.option("--bathrooms", type=int, help="Minimum bathrooms.")
@click.option("--amenities", help="Comma-separated amenities filter.")
@click.option("--superhost", is_flag=True, default=None, help="Only Superhost listings.")
@click.option("--place-id", help="Resolved place id (from `nook place search`).")
@click.option("--bbox", help="Bounding box 'neLat,neLng,swLat,swLng' for map-area search.")
@click.option("--currency", help="ISO currency for prices (e.g. USD).")
@click.option("--cursor", help="Opaque pagination cursor from a prior nextCursor.")
@net_options
@global_options
@click.pass_context
def search(ctx, location, cursor, wait, max_wait, **filters):
    """Search Airbnb listings in a location (discovery)."""
    rt = make_runtime(ctx)
    provided = {k: v for k, v in filters.items() if v is not None and k not in _GLOBAL_KEYS}
    provided["_page_size"] = rt.out.limit
    client = Client(currency=provided.get("currency"), wait=wait, max_wait_s=max_wait)
    listings, next_cursor = client.search(location, filters=provided, cursor=cursor)
    fence_fields(listings, ["name"], rt.wrap)
    rt.out.emit_read(listings, SCOPE, next_cursor=next_cursor,
                     meta_extra={"currency": provided.get("currency") or "USD"})


# --- place (noun-verb) ------------------------------------------------------

@cli.group()
def place():
    """Resolve locations to place candidates."""


@place.command("search")
@click.argument("query")
@net_options
@global_options
@click.pass_context
def place_search(ctx, query, wait, max_wait, **_):
    """Resolve a location string to place candidates (autocomplete), for deterministic search."""
    rt = make_runtime(ctx)
    client = Client(wait=wait, max_wait_s=max_wait)
    rt.out.emit_read(client.place_search(query), SCOPE)


# --- listing (noun-verb) ----------------------------------------------------

@cli.group()
def listing():
    """Inspect individual listings."""


@listing.command("get")
@click.argument("listing_id")
@net_options
@global_options
@click.pass_context
def listing_get(ctx, listing_id, wait, max_wait, **_):
    """Get full details for one listing by id."""
    rt = make_runtime(ctx)
    client = Client(wait=wait, max_wait_s=max_wait)
    data = client.listing(listing_id)
    if data is None:
        raise not_found("listing", listing_id)
    fence_fields(data, ["name", "description", "houseRules", "host.name", "host.description"], rt.wrap)
    rt.out.emit_read(data, SCOPE)


# --- availability (the wedge) -----------------------------------------------

@cli.command("availability")
@click.argument("listing_id")
@click.option("--months", type=click.IntRange(1, 12), default=1, show_default=True,
              help="Forward months of calendar to fetch (1-12).")
@click.option("--start", help="Start date (YYYY-MM-DD); overrides --months window start.")
@click.option("--end", help="End date (YYYY-MM-DD); overrides --months window end.")
@click.option("--currency", help="ISO currency for prices (e.g. USD).")
@net_options
@global_options
@click.pass_context
def availability(ctx, listing_id, months, start, end, currency, wait, max_wait, **_):
    """Forward per-day availability calendar for a listing (available / min-nights / price)."""
    rt = make_runtime(ctx)
    client = Client(currency=currency, wait=wait, max_wait_s=max_wait)
    days = client.availability(listing_id, months=months, start=start, end=end)
    if days is None:
        raise not_found("listing", listing_id)
    rt.out.emit_read(days, SCOPE, meta_extra={"currency": currency or "USD"})


# --- reviews ----------------------------------------------------------------

@cli.command("reviews")
@click.argument("listing_id")
@click.option("--cursor", help="Opaque pagination cursor from a prior nextCursor.")
@net_options
@global_options
@click.pass_context
def reviews(ctx, listing_id, cursor, wait, max_wait, **_):
    """Recent reviews for a listing (free text is fenced untrusted in agent mode)."""
    rt = make_runtime(ctx)
    client = Client(wait=wait, max_wait_s=max_wait)
    items, next_cursor = client.reviews(listing_id, cursor=cursor)
    fence_fields(items, ["text"], rt.wrap)
    rt.out.emit_read(items, SCOPE, next_cursor=next_cursor)


# --- doctor / schema / agent / version --------------------------------------

@cli.command()
@global_options
@click.pass_context
def doctor(ctx, **_):
    """Diagnose setup and report fixes (connectivity, transport, throttle/breaker state)."""
    rt = make_runtime(ctx)
    checks = rt.client.health()
    ok = all(c["ok"] for c in checks)
    if not ok:
        raise AppError(ExitCode.CONFIG, "DOCTOR_FAILED", "one or more checks failed",
                       "see the failing check's detail")
    rt.out.emit({"ok": True, "checks": checks,
                 "legitimacy": "reads public logged-out data at personal scale; no evasion "
                               "(no proxies/CAPTCHA); circuit-breaks on a block. See `nook agent`."})


@cli.command()
@global_options
@click.pass_context
def schema(ctx, **_):
    """Print the machine-readable command schema (JSON)."""
    rt = make_runtime(ctx)
    info = cli.to_info_dict(click.Context(cli, info_name="nook"))
    rt.out.emit_json({
        "tool": "nook",
        "version": __version__,
        "conformance": {"spec": "agent-cli-guidelines", "version": SPEC, "level": "Full"},
        "readOnly": True,
        "scope": SCOPE,
        "commands": info,
        "exit_codes": exit_table(),
        "safety": {"allow_mutations": rt.allow_mutations, "dry_run": rt.dry_run,
                   "no_input": rt.no_input,
                   "note": "nook is read-only; mutation flags are inert (no command mutates)"},
    })


@cli.command()
@global_options
@click.pass_context
def agent(ctx, **_):
    """Print the bundled agent SKILL.md."""
    rt = make_runtime(ctx)
    rt.out.stdout.write(skill_content())


def _repo_slug() -> str | None:
    """owner/repo parsed from the package's Repository URL metadata, or None."""
    try:
        from importlib import metadata

        for u in metadata.metadata("nook").get_all("Project-URL") or []:
            _, _, url = u.partition(",")
            url = url.strip()
            if "github.com/" in url:
                slug = url.split("github.com/", 1)[1].strip("/").removesuffix(".git")
                parts = slug.split("/")
                if len(parts) >= 2:
                    return f"{parts[0]}/{parts[1]}"
    except Exception:
        pass
    return None


def _safe_release_url(raw: str | None) -> str | None:
    """Allow a NOOK_RELEASES_URL override only over https (any host) or http to localhost (tests).
    A misconfigured/hostile value (file://, http://169.254.169.254, …) is ignored — version
    --check falls back to the default — so the override can't be used for SSRF or local-file reads.
    """
    if not raw:
        return None
    from urllib.parse import urlparse

    u = urlparse(raw)
    if u.scheme == "https":
        return raw
    if u.scheme == "http" and u.hostname in ("localhost", "127.0.0.1", "::1"):
        return raw
    return None


def _latest_release() -> tuple[str | None, str]:
    """(latest tag or None, upgrade command). Network, short timeout, **fail-silent**.

    Release source overridable via NOOK_RELEASES_URL (https, or http to localhost for tests).
    """
    import json as _json
    import os
    import urllib.request

    upgrade = "uv tool install --upgrade nook"
    url = _safe_release_url(os.environ.get("NOOK_RELEASES_URL"))
    if not url:
        slug = _repo_slug()
        if not slug:
            return None, upgrade
        url = f"https://api.github.com/repos/{slug}/releases/latest"
    try:
        req = urllib.request.Request(url, headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "nook-version-check",  # GitHub's REST API rejects requests with no UA
        })
        with urllib.request.urlopen(req, timeout=3) as r:  # noqa: S310 (scheme constrained above)
            data = _json.load(r)
        return (data.get("tag_name") or None), upgrade
    except Exception:
        return None, upgrade


def _update_available(latest: str | None, current: str) -> bool:
    """Dev/source builds never report an update — don't nag them."""
    if not latest or not current or current == "dev":
        return False
    return latest.lstrip("v") != current.lstrip("v")


@cli.command()
@click.option("--check", is_flag=True, help="Check for a newer release (network, short timeout, fail-silent).")
@global_options
@click.pass_context
def version(ctx, check, **_):
    """Print the version, or with --check report whether a newer release exists.

    Update awareness, never self-mutation (contract §11): the tool never auto-updates; it only
    reports the upgrade command for the human / package manager.
    """
    rt = make_runtime(ctx)
    if not check:
        rt.out.emit({"version": __version__})
        return
    latest, upgrade = _latest_release()
    out = {
        "current": __version__,
        "latest": latest,
        "updateAvailable": _update_available(latest, __version__),
        "upgrade": upgrade,
    }
    if latest is None:
        out["note"] = "could not check for updates"
    rt.out.emit(out)


# --- entry / exit mapping ---------------------------------------------------

def run(argv: list[str] | None = None) -> int:
    try:
        # With standalone_mode=False, Click *returns* the code from ctx.exit()/Exit (e.g.
        # --help, --version, or a command that calls ctx.exit(N)) instead of raising — so
        # honor the returned value, don't discard it.
        rv = cli.main(args=argv, standalone_mode=False)
        return rv if isinstance(rv, int) else ExitCode.OK
    except (click.exceptions.Exit, SystemExit) as e:  # --help / --version
        code = getattr(e, "exit_code", getattr(e, "code", 0))
        return int(code or 0)
    except click.UsageError as e:
        click.echo(f"error: {e.format_message()}", err=True)
        return ExitCode.USAGE
    except click.Abort:
        return ExitCode.CANCELLED
    except AppError as e:
        _emit_error(e)
        return e.exit


def _emit_error(e: AppError) -> None:
    if _active is not None and _active.fmt == "json":
        print(json.dumps({"error": e.message, "code": e.code, "remediation": e.remediation},
                         ensure_ascii=False), file=sys.stderr)
    else:
        print(f"error: {e.message}", file=sys.stderr)
        if e.code:
            print(f"  code: {e.code}", file=sys.stderr)
        if e.remediation:
            print(f"  fix:  {e.remediation}", file=sys.stderr)


def main() -> None:
    sys.exit(run())
