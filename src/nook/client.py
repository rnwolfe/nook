"""The real Airbnb client — read-only, over the internal /api/v3 GraphQL the web SPA uses.

Cleanly importable and CLI-independent (clear method surface: search / place_search / listing /
availability / reviews / health). Every method is a GET-equivalent; nothing mutates.

Ported from johnbalvin/pyairbnb mechanics but hardened for agent use:
  - curl_cffi impersonate on EVERY call (the lib only impersonates search — a latent bug);
  - self-healing StaysSearch persisted hash (keyhash.py) → UPSTREAM_DRIFT (20) on rotation we
    can't recover; defensive normalizers so an upstream field rename surfaces as UPSTREAM_DRIFT,
    never a KeyError;
  - cross-process throttle + circuit-breaker on every request (transport.py / throttle.py);
  - no auth, no cookies for search/availability/reviews (public logged-out), no evasion.

Field names in the returned dicts are the append-only output contract (spec.md §Output schema).
"""

from __future__ import annotations

import base64
import re
from datetime import date, datetime
from typing import Any

from . import keyhash, transport
from .errors import upstream_drift

_BASE = "https://www.airbnb.com/api/v3"
_ROOM_ID_RE = re.compile(r"(\d+)\s*$")
_DEFERRED_STATE_RE = re.compile(
    r'<script id="data-deferred-state-0"[^>]*>(.*?)</script>', re.DOTALL)
_CURRENCY_SYMBOLS = {"$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY", "₹": "INR", "R$": "BRL"}


# --- small safe-access helpers ---------------------------------------------

def _dig(obj: Any, *path, default=None):
    cur = obj
    for p in path:
        if isinstance(cur, dict):
            cur = cur.get(p)
        elif isinstance(cur, list) and isinstance(p, int) and -len(cur) <= p < len(cur):
            cur = cur[p]
        else:
            return default
    return cur if cur is not None else default


def _encode_id(room_id: str) -> str:
    return base64.b64encode(f"StayListing:{room_id}".encode()).decode()


def _decode_id(b64: str | None) -> str | None:
    if not b64:
        return None
    try:
        raw = base64.b64decode(b64).decode("utf-8", "ignore")
    except Exception:
        raw = b64
    m = _ROOM_ID_RE.search(raw)
    return m.group(1) if m else None


def _parse_price(s: Any, fallback_currency: str | None) -> dict | None:
    """'$1,234' -> {amount: 1234, currency: 'USD'}. Best-effort; unknown symbol keeps it raw."""
    if not s or not isinstance(s, str):
        return None
    digits = re.sub(r"[^\d]", "", s)
    if not digits:
        return None
    currency = fallback_currency
    for sym, code in _CURRENCY_SYMBOLS.items():
        if sym in s:
            currency = code
            break
    return {"amount": int(digits), "currency": currency}


def _parse_rating(s: Any) -> tuple[float | None, int | None]:
    """'4.95 (123)' or '4,95 (123)' -> (4.95, 123)."""
    if not s or not isinstance(s, str):
        return (None, None)
    norm = s.replace(",", ".")
    rating = None
    rm = re.search(r"(\d+(?:\.\d+)?)", norm)
    if rm:
        rating = float(rm.group(1))
    cm = re.search(r"\((\d[\d.,]*)\)", s)
    count = int(re.sub(r"[^\d]", "", cm.group(1))) if cm else None
    return (rating, count)


def _persisted_qs(operation: str, variables: dict, sha256: str,
                  locale: str = "en", currency: str = "USD") -> tuple[str, dict]:
    """Build the (url, params) for a persisted-query GET (calendar/reviews/pdp)."""
    import json as _json

    url = f"{_BASE}/{operation}/{sha256}/"
    params = {
        "operationName": operation,
        "locale": locale,
        "currency": currency,
        "variables": _json.dumps(variables, separators=(",", ":")),
        "extensions": _json.dumps(
            {"persistedQuery": {"version": 1, "sha256Hash": sha256}}, separators=(",", ":")),
    }
    return url, params


def _is_persisted_query_miss(payload: Any) -> bool:
    errs = payload.get("errors") if isinstance(payload, dict) else None
    if not errs:
        return False
    return any("persistedquery" in str(e.get("message", "")).lower().replace(" ", "")
               or "persistedquerynotfound" in str(e).lower().replace(" ", "")
               for e in errs)


class Client:
    """Read-only Airbnb client. Construct once per process; state is on disk (throttle/breaker)."""

    def __init__(self, currency: str = "USD", locale: str = "en",
                 wait: bool = False, max_wait_s: float = 0.0):
        self.currency = currency or "USD"
        self.locale = locale or "en"
        self.wait = wait
        self.max_wait_s = max_wait_s

    def _headers(self) -> dict:
        return {"X-Airbnb-Api-Key": keyhash.get_api_key(),
                "Content-Type": "application/json", "Accept": "application/json"}

    def _get(self, url: str, params: dict) -> Any:
        return transport.request("GET", url, headers=self._headers(), params=params,
                                 wait=self.wait, max_wait_s=self.max_wait_s)

    def _post(self, url: str, params: dict, body: dict) -> Any:
        return transport.request("POST", url, headers=self._headers(), params=params,
                                 json_body=body, wait=self.wait, max_wait_s=self.max_wait_s)

    # --- search -------------------------------------------------------------

    def search(self, location: str, filters: dict[str, Any] | None = None,
               cursor: str | None = None) -> tuple[list[dict], str | None]:
        filters = filters or {}
        currency = filters.get("currency") or self.currency
        sha = keyhash.search_hash()
        payload = self._run_search(location, filters, cursor, sha, currency)
        if _is_persisted_query_miss(payload):
            sha2 = keyhash.search_hash(force_refresh=True)
            if not sha2 or sha2 == sha:
                raise upstream_drift("StaysSearch persisted-query hash rotated and re-scrape failed")
            payload = self._run_search(location, filters, cursor, sha2, currency)
            if _is_persisted_query_miss(payload):
                raise upstream_drift("StaysSearch rejected even the freshly-scraped hash")
        return self._normalize_search(payload, currency)

    def _run_search(self, location, filters, cursor, sha, currency) -> Any:
        url = f"{_BASE}/StaysSearch/{sha}"
        params = {"operationName": "StaysSearch", "locale": self.locale, "currency": currency}
        raw_params = _build_raw_params(location, filters)
        by_map = any(filters.get(k) is not None for k in ("lat", "lng", "bbox"))
        req = {
            "cursor": cursor or "",
            "requestedPageType": "STAYS_SEARCH",
            "metadataOnly": False,
            "source": "structured_search_input_header",
            "searchType": "user_map_move" if by_map else "filter_change",
            "treatmentFlags": _TREATMENT_FLAGS,
            "rawParams": raw_params,
        }
        body = {
            "operationName": "StaysSearch",
            "extensions": {"persistedQuery": {"version": 1, "sha256Hash": sha}},
            "variables": {
                "includeMapResults": by_map,
                "isLeanTreatment": False,
                "skipExtendedSearchParams": False,
                "staysSearchRequest": req,
                "staysMapSearchRequestV2": {**req, "maxMapItems": 9999} if by_map else req,
            },
        }
        return self._post(url, params, body)

    def _normalize_search(self, payload: Any, currency: str) -> tuple[list[dict], str | None]:
        results = _dig(payload, "data", "presentation", "staysSearch", "results", "searchResults")
        if results is None:
            # Distinguish "no results" from "shape changed": if the staysSearch node is entirely
            # absent, the contract drifted.
            if _dig(payload, "data", "presentation", "staysSearch") is None:
                raise upstream_drift("StaysSearch response missing the expected results node")
            results = []
        out: list[dict] = []
        for r in results:
            if not isinstance(r, dict) or r.get("__typename") != "StaySearchResult":
                continue
            dsl = r.get("demandStayListing", {}) or {}
            room_id = _decode_id(dsl.get("id"))
            pr = r.get("structuredDisplayPrice", {}) or {}
            price_str = _dig(pr, "primaryLine", "originalPrice") or _dig(pr, "primaryLine", "price")
            rating, count = _parse_rating(r.get("avgRatingLocalized"))
            badges = [b.get("loggingContext", {}).get("badgeType")
                      for b in (r.get("badges") or []) if isinstance(b, dict)]
            badges = [b for b in badges if b]
            out.append({
                "id": room_id,
                "name": _dig(dsl, "description", "name", "localizedStringWithTranslationPreference")
                or r.get("title"),
                "roomType": _dig(r, "structuredContent", "primaryLine", "body"),  # often None in search
                "price": {**(_parse_price(price_str, currency) or {"amount": None, "currency": currency}),
                          "qualifier": _dig(pr, "primaryLine", "qualifier")},
                "rating": rating,
                "reviewsCount": count,
                "coordinates": {"lat": _dig(dsl, "location", "coordinate", "latitude"),
                                "lng": _dig(dsl, "location", "coordinate", "longitude")},
                "badges": badges,
                "superhost": any("SUPERHOST" in str(b).upper() for b in badges),
                "url": f"https://www.airbnb.com/rooms/{room_id}" if room_id else None,
            })
        cursor = _dig(payload, "data", "presentation", "staysSearch", "results",
                      "paginationInfo", "nextPageCursor")
        return out, cursor

    # --- place autocomplete (discovery aid) --------------------------------

    def place_search(self, query: str) -> list[dict]:
        """Resolve a location string to place candidates (Airbnb autocomplete). Best-effort:
        returns placeId + name; coordinates/bbox are not exposed by autocomplete (declared null).
        `nook search <location>` accepts the raw string directly, so this is a convenience."""
        key = keyhash.get_api_key()
        markets = self._get("https://www.airbnb.com/api/v2/user_markets",
                            {"currency": self.currency, "locale": self.locale,
                             "language": "en", "key": key})
        token = _dig(markets, "user_markets", 0, "satori_parameters")
        params = {
            "currency": self.currency, "locale": self.locale, "language": "en", "key": key,
            "num_results": 10, "user_input": query, "api_version": "1.2.0",
            "satori_config_token": token, "region": "-1", "vertical_refinement": "homes",
            "options": "should_filter_by_vertical_refinement",
        }
        data = self._get("https://www.airbnb.com/api/v2/autocompletes-personalized", params)
        terms = _dig(data, "autocomplete_terms", default=[])
        out = []
        for t in terms if isinstance(terms, list) else []:
            if not isinstance(t, dict):
                continue
            out.append({
                "placeId": _dig(t, "location", "google_place_id"),
                "name": _dig(t, "location", "location_name") or t.get("display_name"),
                "type": t.get("type"),
                "coordinates": None,   # not provided by autocomplete
                "bbox": None,
            })
        return out

    # --- availability (the wedge) ------------------------------------------

    def availability(self, listing_id: str, months: int = 1,
                     start: str | None = None, end: str | None = None) -> list[dict] | None:
        today = datetime.now()
        variables = {"request": {"count": max(1, min(12, months)),
                                 "listingId": str(listing_id),
                                 "month": today.month, "year": today.year}}
        url, params = _persisted_qs("PdpAvailabilityCalendar",
                                    variables, keyhash.HASHES["PdpAvailabilityCalendar"],
                                    locale=self.locale, currency=self.currency)
        payload = self._get(url, params)
        cal = _dig(payload, "data", "merlin", "pdpAvailabilityCalendar", "calendarMonths")
        if cal is None:
            if _dig(payload, "data", "merlin") is None and _dig(payload, "data") is not None:
                raise upstream_drift("PdpAvailabilityCalendar response shape changed")
            return None  # unknown/removed listing
        days = _normalize_calendar(cal, self.currency)
        lo = _parse_date(start)
        hi = _parse_date(end) or _add_months(date.today(), max(1, min(12, months)))
        lo = lo or date.today()
        days = [d for d in days if lo <= _parse_date(d["date"]) <= hi] if days else days
        return days

    # --- reviews -----------------------------------------------------------

    def reviews(self, listing_id: str, cursor: str | None = None) -> tuple[list[dict], str | None]:
        offset = int(cursor) if (cursor and cursor.isdigit()) else 0
        limit = 50
        variables = {
            "id": _encode_id(str(listing_id)),
            "pdpReviewsRequest": {
                "fieldSelector": "for_p3_translation_only", "forPreview": False,
                "limit": limit, "offset": str(offset), "showingTranslationButton": False,
                "first": limit, "sortingPreference": "MOST_RECENT",
                "numberOfAdults": "1", "numberOfChildren": "0", "numberOfInfants": "0",
                "numberOfPets": "0", "after": None,
            },
        }
        url, params = _persisted_qs("StaysPdpReviewsQuery", variables,
                                    keyhash.HASHES["StaysPdpReviewsQuery"],
                                    locale=self.locale, currency=self.currency)
        payload = self._get(url, params)
        raw = _dig(payload, "data", "presentation", "stayProductDetailPage", "reviews", "reviews")
        if raw is None:
            if _dig(payload, "data", "presentation", "stayProductDetailPage") is None:
                raise upstream_drift("reviews response shape changed")
            return ([], None)
        items = [{
            "id": rv.get("id"),
            "date": rv.get("createdAt") or rv.get("localizedDate"),
            "rating": rv.get("rating"),
            "language": rv.get("language"),
            "text": rv.get("comments") or _dig(rv, "localizedReview", "comments"),
            "reviewer": {"firstName": _dig(rv, "reviewer", "firstName")},
        } for rv in raw if isinstance(rv, dict)]
        next_cursor = str(offset + limit) if len(items) >= limit else None
        return items, next_cursor

    # --- listing details (PDP HTML embedded state) -------------------------

    def listing(self, listing_id: str) -> dict | None:
        html = transport.request("GET", f"https://www.airbnb.com/rooms/{listing_id}",
                                 expect_json=False, wait=self.wait, max_wait_s=self.max_wait_s)
        m = _DEFERRED_STATE_RE.search(html or "")
        if not m:
            # Could be a genuine 404 page (unknown listing) or a shape change. A valid room page
            # always ships this script, so treat a 200-without-it as not-found for the agent.
            return None
        import json as _json

        try:
            meta = _json.loads(m.group(1))
            root = _dig(meta, "niobeClientData", 0, 1) or meta
        except Exception as e:
            raise upstream_drift("could not parse the listing page state blob") from e
        return _normalize_listing(root, listing_id, self.currency)

    # --- doctor ------------------------------------------------------------

    def health(self) -> list[dict]:
        from . import throttle
        checks: list[dict] = []
        # Transport / TLS-impersonation presence (no network).
        try:
            import curl_cffi  # noqa: F401
            checks.append({"name": "transport", "ok": True,
                           "detail": "curl_cffi present (Chrome TLS impersonation available)"})
        except Exception:
            checks.append({"name": "transport", "ok": False,
                           "detail": "curl_cffi missing — reinstall nook (uv tool install --upgrade nook)"})
        # Circuit-breaker state (no network).
        b = throttle.breaker_state()
        checks.append({"name": "circuit_breaker",
                       "ok": not b["tripped"],
                       "detail": (f"tripped — {b['remaining_s']}s cooldown remaining ({b['reason']})"
                                  if b["tripped"] else "closed")})
        # Key/hash cache freshness (no network probe while a breaker is open).
        c = keyhash._cache()
        checks.append({"name": "key_cache", "ok": True,
                       "detail": ("cached" if c.get("api_key") else "will scrape the public key on first call")})
        checks.append({"name": "auth", "ok": True, "detail": "no auth required (public logged-out access)"})
        return checks


# --- module-level normalizers / builders -----------------------------------

_TREATMENT_FLAGS = [
    "feed_map_decouple_m11_treatment",
    "stays_search_rehydration_treatment_desktop",
    "stays_search_rehydration_treatment_moweb",
    "selective_query_feed_map_homepage_desktop_treatment",
    "selective_query_feed_map_homepage_moweb_treatment",
]

_ROOM_TYPE_MAP = {"entire": "Entire home/apt", "private": "Private room",
                  "shared": "Shared room", "hotel": "Hotel room"}


def _rp(name: str, *values) -> dict:
    return {"filterName": name, "filterValues": [str(v) for v in values]}


def _build_raw_params(location: str, f: dict[str, Any]) -> list[dict]:
    """Build the StaysSearch rawParams list. Uses `query` for text search (no bbox required);
    adds geo params only when a bbox/point is supplied. Stale pyairbnb placeholders are dropped."""
    params: list[dict] = [
        _rp("cdnCacheSafe", "false"), _rp("channel", "EXPLORE"),
        _rp("datePickerType", "calendar"), _rp("flexibleTripLengths", "one_week"),
        _rp("itemsPerGrid", str(f.get("_page_size", 50))),
        _rp("priceFilterInputType", "0"), _rp("refinementPaths", "/homes"),
        _rp("screenSize", "large"), _rp("tabId", "home_tab"), _rp("version", "1.8.3"),
    ]
    if f.get("place_id"):
        params.append(_rp("placeId", f["place_id"]))
    if any(f.get(k) is not None for k in ("lat", "lng", "bbox")):
        params.append(_rp("searchByMap", "true"))
        if f.get("bbox"):
            try:
                ne_lat, ne_lng, sw_lat, sw_lng = [x.strip() for x in str(f["bbox"]).split(",")]
                params += [_rp("neLat", ne_lat), _rp("neLng", ne_lng),
                           _rp("swLat", sw_lat), _rp("swLng", sw_lng)]
            except ValueError:
                pass
    else:
        params.append(_rp("searchByMap", "false"))
        params.append(_rp("query", location))
    if f.get("checkin") and f.get("checkout"):
        nights = _nights(f["checkin"], f["checkout"])
        params += [_rp("checkin", f["checkin"]), _rp("checkout", f["checkout"])]
        if nights:
            params.append(_rp("priceFilterNumNights", nights))
    rt = _ROOM_TYPE_MAP.get(f.get("room_type"))
    if rt:
        params += [_rp("room_types", rt), _rp("selected_filter_order", f"room_types:{rt}")]
    for key, fname in (("min_price", "price_min"), ("max_price", "price_max"),
                       ("adults", "adults"), ("children", "children"), ("infants", "infants"),
                       ("pets", "pets"), ("bedrooms", "min_bedrooms"), ("beds", "min_beds"),
                       ("bathrooms", "min_bathrooms")):
        if f.get(key) is not None:
            params.append(_rp(fname, f[key]))
    if f.get("guests") is not None and f.get("adults") is None:
        params.append(_rp("adults", f["guests"]))
    if f.get("amenities"):
        for a in str(f["amenities"]).split(","):
            a = a.strip()
            if a:
                params += [_rp("amenities", a), _rp("selected_filter_order", f"amenities:{a}")]
    if f.get("superhost"):
        params.append(_rp("superhost", "true"))
    return params


def _normalize_calendar(calendar_months: list, currency: str) -> list[dict]:
    days: list[dict] = []
    for month in calendar_months or []:
        for d in (month.get("days") or []) if isinstance(month, dict) else []:
            if not isinstance(d, dict):
                continue
            price = d.get("price")
            price_obj = None
            if isinstance(price, dict):
                price_obj = _parse_price(
                    price.get("localPriceFormatted") or price.get("priceString"), currency)
            days.append({
                "date": d.get("calendarDate"),
                "available": d.get("available"),
                "availableForCheckin": d.get("availableForCheckin"),
                "availableForCheckout": d.get("availableForCheckout"),
                "bookable": d.get("bookable"),
                "minNights": d.get("minNights"),
                "maxNights": d.get("maxNights"),
                "price": price_obj,
            })
    return days


_CAP_RE = {"bedrooms": re.compile(r"(\d+)\s+bedroom"), "beds": re.compile(r"(\d+)\s+bed(?!room)"),
           "baths": re.compile(r"(\d+(?:\.\d+)?)\s+(?:private |shared )?bath")}


def _normalize_listing(root: Any, listing_id: str, currency: str) -> dict:
    """Normalize the PDP embedded state. High-confidence fields come from metadata
    (eventDataLogging + sharingConfig); section bodies are keyed by `sectionId` (live sections all
    share __typename="SectionContainer"). Anything absent/lazy-loaded defaults to null/[]."""
    spdp = _dig(root, "data", "presentation", "stayProductDetailPage") or {}
    md = _dig(spdp, "sections", "metadata") or {}
    ev = _dig(md, "loggingContext", "eventDataLogging") or {}
    sc = md.get("sharingConfig") or {}
    by_id = {s.get("sectionId"): (s.get("section") or {})
             for s in (_dig(spdp, "sections", "sections") or []) if isinstance(s, dict)}

    title = sc.get("title")
    cap = {"guests": ev.get("personCapacity") or sc.get("personCapacity"),
           "bedrooms": None, "beds": None, "baths": None}
    for k, rx in _CAP_RE.items():
        m = rx.search(title or "")
        if m:
            cap[k] = float(m.group(1)) if k == "baths" else int(m.group(1))

    host_card = by_id.get("MEET_YOUR_HOST", {}).get("cardData") or {}
    policies = by_id.get("POLICIES_DEFAULT", {})
    cancel = policies.get("cancellationPolicyForDisplay")
    if isinstance(cancel, dict):
        cancel = cancel.get("title") or cancel.get("cancellationPolicyForDisplay")

    return {
        "id": str(listing_id),
        "name": title,
        "description": _dig(by_id.get("DESCRIPTION_DEFAULT", {}), "htmlDescription", "htmlText"),
        "host": {"id": _decode_id(host_card.get("userId")),
                 "name": host_card.get("name"),
                 "isSuperhost": host_card.get("isSuperhost", ev.get("isSuperhost")),
                 "description": by_id.get("MEET_YOUR_HOST", {}).get("about")},
        "roomType": ev.get("roomType") or sc.get("propertyType"),
        "capacity": cap,
        "amenities": _listing_amenities(by_id),
        "houseRules": policies.get("additionalHouseRules"),
        "location": {"lat": ev.get("listingLat"), "lng": ev.get("listingLng"),
                     "city": by_id.get("LOCATION_DEFAULT", {}).get("subtitle")},
        "rating": {"overall": ev.get("guestSatisfactionOverall"),
                   "breakdown": {"cleanliness": ev.get("cleanlinessRating"),
                                 "accuracy": ev.get("accuracyRating"),
                                 "checkin": ev.get("checkinRating"),
                                 "communication": ev.get("communicationRating"),
                                 "location": ev.get("locationRating"),
                                 "value": ev.get("valueRating")}},
        "reviewsCount": ev.get("visibleReviewCount") or sc.get("reviewCount"),
        "photos": [mi.get("baseUrl") for mi in
                   (by_id.get("PHOTO_TOUR_SCROLLABLE_MODAL", {}).get("mediaItems") or [])
                   if isinstance(mi, dict) and mi.get("baseUrl")],
        "price": None,  # nightly price is date-dependent — use `nook availability`
        "cancellationPolicy": cancel,
        "url": f"https://www.airbnb.com/rooms/{listing_id}",
    }


def _listing_amenities(by_id: dict) -> list[str]:
    """Amenities from the PDP when inline; the full set is lazy-loaded behind AMENITIES_DEFAULT,
    so this is best-effort (often empty). `AMENITIES_DEFAULT.seeAllAmenitiesGroups` when present."""
    groups = _dig(by_id.get("AMENITIES_DEFAULT", {}), "seeAllAmenitiesGroups") or []
    names: list[str] = []
    for g in groups:
        for a in (g.get("amenities") or []) if isinstance(g, dict) else []:
            if isinstance(a, dict) and a.get("available") and a.get("title"):
                names.append(a["title"])
    return names


# --- date helpers -----------------------------------------------------------

def _parse_date(s: str | None):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _nights(checkin: str, checkout: str) -> int | None:
    ci, co = _parse_date(checkin), _parse_date(checkout)
    if ci and co and co > ci:
        return (co - ci).days
    return None


def _add_months(d: date, months: int) -> date:
    m = d.month - 1 + months
    year = d.year + m // 12
    month = m % 12 + 1
    return date(year, month, 28)  # 28 keeps it valid across month lengths; window upper-bound only
