"""Stable exit-code table and the structured CLI error type. See contract.md §3, §4.

nook is 100% read-only. The auth/permission/mutation codes are present for contract
uniformity and documented as N/A; the target-specific addition is UPSTREAM_DRIFT (20).
"""

from __future__ import annotations


class ExitCode:
    OK = 0
    GENERIC = 1
    USAGE = 2
    EMPTY = 3
    AUTH = 4  # N/A — nook needs no auth (public logged-out access)
    NOT_FOUND = 5
    PERM = 6  # N/A — no permissioned resources
    RATE = 7  # rate limited / blocked — circuit-break on 403 challenge / 429 / CAPTCHA
    RETRY = 8
    CONFIG = 10
    MUTATION_BLOCKED = 12  # N/A — nook has no mutations (present for contract uniformity)
    INPUT_REQUIRED = 13
    UPSTREAM_DRIFT = 20  # target-specific: public key/persisted-hash scrape or response shape broke
    CANCELLED = 130


def exit_table() -> dict[str, int]:
    return {
        "ok": ExitCode.OK,
        "generic_error": ExitCode.GENERIC,
        "usage": ExitCode.USAGE,
        "empty_results": ExitCode.EMPTY,
        "auth_required": ExitCode.AUTH,
        "not_found": ExitCode.NOT_FOUND,
        "permission": ExitCode.PERM,
        "rate_limited": ExitCode.RATE,
        "retryable": ExitCode.RETRY,
        "config_error": ExitCode.CONFIG,
        "mutation_blocked": ExitCode.MUTATION_BLOCKED,
        "input_required": ExitCode.INPUT_REQUIRED,
        "upstream_drift": ExitCode.UPSTREAM_DRIFT,
        "cancelled": ExitCode.CANCELLED,
    }


class AppError(Exception):
    """Structured error carrying a machine code, remediation, and process exit code."""

    def __init__(self, exit_code: int, code: str, message: str, remediation: str = ""):
        super().__init__(message)
        self.exit = exit_code
        self.code = code
        self.message = message
        self.remediation = remediation


def mutation_blocked(op: str) -> AppError:
    return AppError(
        ExitCode.MUTATION_BLOCKED,
        "MUTATION_BLOCKED",
        f"{op} is a mutating operation and is blocked by default",
        "re-run with --allow-mutations (add --dry-run to preview)",
    )


def not_found(kind: str, ident: str) -> AppError:
    return AppError(
        ExitCode.NOT_FOUND, "NOT_FOUND", f"{kind} {ident} not found",
        f"verify the {kind} id — it may be invalid, private, or removed",
    )


def input_required(what: str) -> AppError:
    return AppError(
        ExitCode.INPUT_REQUIRED, "INPUT_REQUIRED", f"{what} is required",
        "pass it as a flag/argument (running with --no-input, so prompts are disabled)",
    )


def rate_limited(detail: str = "") -> AppError:
    """Circuit-break: Airbnb returned a block/challenge (403 / 429 / CAPTCHA). Do NOT retry
    into it — stop and let the throttle window pass (contract §12)."""
    msg = "blocked by Airbnb (rate limit or bot challenge)"
    return AppError(
        ExitCode.RATE, "RATE_LIMITED", f"{msg}{': ' + detail if detail else ''}",
        "stop and retry later at lower volume; nook self-throttles and will not evade the block",
    )


def upstream_drift(detail: str = "") -> AppError:
    """Airbnb changed its internals (public API key / persisted-query hash / response shape).
    Distinct from a transient block so an agent can tell 'the tool needs an update' from
    'I'm being throttled'."""
    return AppError(
        ExitCode.UPSTREAM_DRIFT, "UPSTREAM_DRIFT",
        f"Airbnb's internal API shape changed{': ' + detail if detail else ''}",
        "update nook to a newer release (uv tool install --upgrade nook); this is not a rate limit",
    )
