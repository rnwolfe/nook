"""Self-healing public API key + persisted-query hashes (contract §12, spec.md §Target).

Airbnb's web SPA authenticates to its own `/api/v3` GraphQL with a PUBLIC static API key it ships
to every anonymous visitor, and each operation is a persisted query identified by a sha256 hash.
The `StaysSearch` hash rotates; the others have been stable. We:

  - scrape the key live from the homepage (regex), cache it in $XDG_STATE_HOME/nook/, and fall
    back to a long-known public value if the scrape misses;
  - keep the known-good persisted hashes, and *self-heal* the rotating StaysSearch hash: on a
    PersistedQueryNotFound, re-scrape from the JS bundle and retry once; if that fails, the client
    raises UPSTREAM_DRIFT (exit 20) — distinct from a rate-limit.

This is not evasion: the key is public and the hashes are the ones the real web client uses. We
present the genuine client, at low volume; we do not disguise identity.
"""

from __future__ import annotations

import re
import time

from . import state, transport

# Long-stable public web key (shipped to every anonymous visitor). Fallback only — we prefer the
# live-scraped value so a rotation self-heals.
FALLBACK_API_KEY = "d306zoyjsyarp7ifhu67rjxn52tv0t20"

# Known-good persisted-query hashes. StaysSearch is the one that rotates (self-healed below).
HASHES = {
    "StaysSearch": "9f945886dcc032b9ef4ba770d9132eb0aa78053296b5405483944c229617b00b",
    "PdpAvailabilityCalendar": "8f08e03c7bd16fcad3c92a3592c19a8b559a0d0855a84028d1163d4733ed9ade",
    "StaysPdpReviewsQuery": "dec1c8061483e78373602047450322fd474e79ba9afa8d3dbbc27f504030f91d",
    "StaysPdpSections": "80c7889b4b0027d99ffea830f6c0d4911a6e863a957cbe1044823f0fc746bf1f",
}

_CACHE_FILE = "keyhash.json"
_KEY_TTL_S = 24 * 3600
_HOME = "https://www.airbnb.com"

_KEY_RE = re.compile(r'"api_config":\{"key":"([^"]+)"')
_ENTRY_BUNDLE_RE = re.compile(
    r"https://a0\.muscache\.com/airbnb/static/packages/web/[^\"']+"
    r"asyncRequire\.[^\"']+\.js")
_HASH_NEAR_SEARCH_RE = re.compile(r'StaysSearch["\'/][^0-9a-f]{0,40}([0-9a-f]{64})')
_HASH_URL_RE = re.compile(r'/api/v3/StaysSearch/([0-9a-f]{64})')


def _cache() -> dict:
    return state.read_json(_CACHE_FILE, {}) or {}


def get_api_key(force: bool = False) -> str:
    """Live-scraped public key (cached with TTL); falls back to the long-known value."""
    c = _cache()
    if not force and c.get("api_key") and (time.time() - c.get("api_key_ts", 0) < _KEY_TTL_S):
        return c["api_key"]
    try:
        html = transport.request("GET", _HOME, expect_json=False)
        m = _KEY_RE.search(html or "")
        if m:
            key = m.group(1)
            with state.update_json(_CACHE_FILE, {}) as box:
                box[0] = {**(box[0] or {}), "api_key": key, "api_key_ts": time.time()}
            return key
    except Exception:
        pass  # fall through to the known public key — never hard-fail on the key alone
    return c.get("api_key") or FALLBACK_API_KEY


def search_hash(force_refresh: bool = False) -> str:
    """The current StaysSearch persisted hash: cached-scraped value, else the known-good default."""
    c = _cache()
    if not force_refresh and c.get("search_hash"):
        return c["search_hash"]
    scraped = _scrape_search_hash() if force_refresh else None
    if scraped:
        with state.update_json(_CACHE_FILE, {}) as box:
            box[0] = {**(box[0] or {}), "search_hash": scraped, "search_hash_ts": time.time()}
        return scraped
    return c.get("search_hash") or HASHES["StaysSearch"]


def _scrape_search_hash() -> str | None:
    """Best-effort live re-scrape of the rotating StaysSearch hash from the JS bundles.

    Fetch the homepage, follow the entry bundle, and look for the operation's 64-hex id near a
    `StaysSearch` reference. Fragile by nature — any miss returns None and the client escalates to
    UPSTREAM_DRIFT so an agent knows the tool needs an update rather than a back-off.
    """
    try:
        html = transport.request("GET", _HOME, expect_json=False) or ""
        for src in (html, *(_fetch_bundles(html))):
            for rx in (_HASH_URL_RE, _HASH_NEAR_SEARCH_RE):
                m = rx.search(src)
                if m:
                    return m.group(1)
    except Exception:
        return None
    return None


def _fetch_bundles(html: str) -> list[str]:
    out: list[str] = []
    for url in dict.fromkeys(_ENTRY_BUNDLE_RE.findall(html)):
        try:
            out.append(transport.request("GET", url, expect_json=False) or "")
        except Exception:
            continue
        if len(out) >= 3:  # bound the walk — don't hammer the CDN
            break
    return out
