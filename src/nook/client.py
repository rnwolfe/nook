"""PLACEHOLDER Airbnb client — canned fixtures so the scaffold runs and is testable offline.

cli-implement REPLACES this with the real client:
  - HTTP via curl_cffi (impersonate="chrome") — TLS/JA3 must match a real browser or Airbnb
    403s at the transport layer (spec.md §Language; the ratified §12 boundary).
  - Airbnb internal GraphQL: StaysSearch, PdpAvailabilityCalendar, StaysPdpSections,
    autocompletes-personalized. Public static X-Airbnb-Api-Key + rotating StaysSearch
    persisted-query hash, both scraped live and cached in $XDG_STATE_HOME/nook/ (self-healing).
  - Cross-process throttle + circuit-breaker state persisted in $XDG_STATE_HOME/nook/ (an agent
    spawns a fresh process per call, so an in-memory timer is a no-op) — contract §12.
  - Raises errors.rate_limited() on a 403 challenge / 429 / CAPTCHA (circuit-break, exit 7) and
    errors.upstream_drift() when the key/hash scrape or response shape breaks (exit 20).

The method surface below is the contract the real client must satisfy. Return shapes match
spec.md §Output schema. Free-text fields (name/description/houseRules/review text) are fenced as
untrusted by cli-implement (contract §8); the placeholder leaves them plain.
"""

from __future__ import annotations

from typing import Any

# A single stub listing id the placeholder "knows about", so `listing get`/`availability` can
# demonstrate both the found and not-found paths offline.
_STUB_ID = "12345678"


class Client:
    """Read-only Airbnb client. Every method is a GET-equivalent; nothing mutates."""

    def search(self, location: str, filters: dict[str, Any] | None = None,
               cursor: str | None = None) -> tuple[list[dict], str | None]:
        """Search listings. Returns (listings, nextCursor). PLACEHOLDER."""
        return (
            [
                {
                    "id": _STUB_ID,
                    "name": "[stub] Sunny 1BR near the center",
                    "roomType": "entire_home",
                    "price": {"amount": 128, "currency": "USD", "qualifier": "night"},
                    "rating": 4.92,
                    "reviewsCount": 214,
                    "coordinates": {"lat": 38.7169, "lng": -9.1399},
                    "badges": ["Superhost"],
                    "superhost": True,
                    "url": f"https://www.airbnb.com/rooms/{_STUB_ID}",
                }
            ],
            None,
        )

    def place_search(self, query: str) -> list[dict]:
        """Resolve a location string to place candidates. PLACEHOLDER."""
        return [
            {
                "placeId": "ChIJ_stub",
                "name": f"[stub] {query}",
                "type": "city",
                "coordinates": {"lat": 38.7223, "lng": -9.1393},
                "bbox": {"ne": {"lat": 38.80, "lng": -9.09}, "sw": {"lat": 38.69, "lng": -9.23}},
            }
        ]

    def listing(self, listing_id: str) -> dict | None:
        """Full listing details, or None if not found. PLACEHOLDER."""
        if listing_id != _STUB_ID:
            return None
        return {
            "id": _STUB_ID,
            "name": "[stub] Sunny 1BR near the center",
            "description": "[stub] A bright apartment. (cli-implement fences this untrusted text.)",
            "host": {"id": "h_stub", "name": "[stub] Ana", "isSuperhost": True},
            "roomType": "entire_home",
            "capacity": {"guests": 2, "bedrooms": 1, "beds": 1, "baths": 1},
            "amenities": ["Wifi", "Kitchen", "Washer"],
            "houseRules": "[stub] No smoking.",
            "location": {"lat": 38.7169, "lng": -9.1399, "city": "Lisbon"},
            "rating": {"overall": 4.92, "breakdown": {"cleanliness": 4.9, "location": 5.0}},
            "reviewsCount": 214,
            "photos": [f"https://example.com/photo/{_STUB_ID}.jpg"],
            "price": {"amount": 128, "currency": "USD", "qualifier": "night"},
            "cancellationPolicy": "moderate",
            "url": f"https://www.airbnb.com/rooms/{_STUB_ID}",
        }

    def availability(self, listing_id: str, months: int = 1,
                     start: str | None = None, end: str | None = None) -> list[dict] | None:
        """Forward per-day availability calendar, or None if the listing is unknown. PLACEHOLDER."""
        if listing_id != _STUB_ID:
            return None
        return [
            {
                "date": "2026-08-01",
                "available": True,
                "availableForCheckin": True,
                "availableForCheckout": False,
                "bookable": True,
                "minNights": 2,
                "maxNights": 28,
                "price": {"amount": 128, "currency": "USD"},
            },
            {
                "date": "2026-08-02",
                "available": False,
                "availableForCheckin": False,
                "availableForCheckout": True,
                "bookable": False,
                "minNights": 2,
                "maxNights": 28,
                "price": None,
            },
        ]

    def reviews(self, listing_id: str, cursor: str | None = None) -> tuple[list[dict], str | None]:
        """Recent reviews (fenced untrusted by cli-implement). Returns (reviews, nextCursor)."""
        if listing_id != _STUB_ID:
            return ([], None)
        return (
            [
                {
                    "id": "r_stub",
                    "date": "2026-06-14",
                    "rating": 5,
                    "language": "en",
                    "text": "[stub] Lovely stay. (cli-implement fences this untrusted text.)",
                    "reviewer": {"firstName": "[stub] Sam"},
                }
            ],
            None,
        )

    def health(self) -> list[dict]:
        """doctor checks. The real client verifies TLS-impersonation availability, key/hash
        cache freshness, and circuit-breaker state. PLACEHOLDER reports the scaffold state."""
        return [
            {"name": "transport", "ok": True,
             "detail": "placeholder client (cli-implement wires curl_cffi impersonate=chrome)"},
            {"name": "auth", "ok": True, "detail": "no auth required (public logged-out access)"},
        ]
