"""HTTP transport: curl_cffi with a real Chrome TLS/JA3 fingerprint.

Airbnb's edge (HUMAN/PerimeterX) 403s any non-browser TLS handshake, so a plain requests/httpx
client is dead on arrival. curl_cffi `impersonate="chrome"` presents the SAME TLS profile the real
web client sends — the ratified §12 boundary: match the genuine client, don't disguise identity.
No proxies, no IP rotation, no CAPTCHA solving.

Responsibilities:
- throttle before every request (cross-process spacing + circuit-breaker) — throttle.py
- classify the response into typed domain errors:
    403 / 429 / bot-challenge body  -> rate_limited (exit 7) + trip the breaker (do NOT retry in)
    5xx / network                   -> bounded retry with backoff, then retryable (exit 8)
- never leak a curl_cffi stack trace; the client layer maps shape problems to upstream_drift (20).
"""

from __future__ import annotations

import time
from typing import Any

from . import throttle
from .errors import AppError, ExitCode

_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
_IMPERSONATE = "chrome124"
_TIMEOUT_S = 15
_MAX_RETRIES = 2  # for transient 5xx/network only — NEVER for a block
_CHALLENGE_MARKERS = ("px-captcha", "captcha-container", "Press & Hold", "_pxhc",
                      "perimeterx", "Access to this page has been denied")


def _retryable(msg: str) -> AppError:
    return AppError(ExitCode.RETRY, "RETRYABLE", msg,
                    "transient upstream error; retry shortly")


def _session():
    # Lazy import so --help / schema stay fast and the dep is only needed at call time.
    from curl_cffi import requests as cffi

    return cffi.Session(impersonate=_IMPERSONATE, timeout=_TIMEOUT_S)


def _looks_challenged(status: int, text: str) -> bool:
    if status in (403, 429):
        return True
    # A 200 that is an HTML anti-bot interstitial rather than JSON.
    head = text[:2000]
    return any(m.lower() in head.lower() for m in _CHALLENGE_MARKERS)


def _handle_block(status: int, headers: dict) -> None:
    ra = headers.get("Retry-After") or headers.get("retry-after")
    retry_after = None
    if ra:
        try:
            retry_after = float(ra)
        except (TypeError, ValueError):
            retry_after = None
    reason = f"HTTP {status}" if status else "bot challenge"
    throttle.trip_breaker(reason, retry_after_s=retry_after)
    from .errors import rate_limited

    err = rate_limited(reason)
    if retry_after:
        err.remediation = (f"blocked; retry after ~{round(retry_after)}s at lower volume "
                           f"(nook tripped its breaker and will not evade)")
    raise err


def request(method: str, url: str, *, headers: dict | None = None, params: dict | None = None,
            json_body: Any = None, wait: bool = False, max_wait_s: float = 0.0,
            expect_json: bool = True) -> Any:
    """Perform one upstream request through the throttle + breaker, returning parsed JSON
    (or raw text if expect_json=False). Raises typed AppErrors; never leaks curl_cffi internals."""
    base_headers = {"User-Agent": _UA, "Accept-Language": "en-US,en;q=0.9"}
    if headers:
        base_headers.update(headers)

    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES + 1):
        throttle.before_request(wait=wait, max_wait_s=max_wait_s)
        try:
            sess = _session()
            resp = sess.request(method, url, headers=base_headers, params=params, json=json_body)
        except AppError:
            raise
        except Exception as e:  # network/TLS/timeout — transient
            last_exc = e
            if attempt < _MAX_RETRIES:
                time.sleep(2 ** attempt)
                continue
            raise _retryable(f"network error contacting Airbnb: {type(e).__name__}") from e

        status = resp.status_code
        text = resp.text or ""
        if _looks_challenged(status, text):
            _handle_block(status, dict(resp.headers))  # raises (exit 7) — no retry into a block
        if status >= 500:
            last_exc = _retryable(f"Airbnb returned HTTP {status}")
            if attempt < _MAX_RETRIES:
                time.sleep(2 ** attempt)
                continue
            raise last_exc
        if status >= 400:
            # 404 etc. — let the client layer decide (e.g. NOT_FOUND); surface status+body.
            raise AppError(ExitCode.GENERIC, "HTTP_ERROR", f"Airbnb returned HTTP {status}",
                           "verify the request; if this persists the API may have changed")
        if not expect_json:
            return text
        try:
            return resp.json()
        except Exception as e:
            # A 200 that isn't JSON is usually a soft block or a shape change.
            if _looks_challenged(200, text):
                _handle_block(200, dict(resp.headers))
            from .errors import upstream_drift

            raise upstream_drift("expected JSON but got a non-JSON response") from e
    # Unreachable, but keep the type-checker happy.
    raise _retryable(str(last_exc) if last_exc else "unknown transport error")
