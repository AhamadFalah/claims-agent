"""AfterShip tracking lookup — verifies a parcel's real carrier status.

Given a tracking number, returns the live AfterShip tag + last checkpoint so the
agent can confirm a claim against carrier data before submitting to Evri. No-ops
(returns None) when AFTERSHIP_API_KEY is unset, so the pipeline falls back to
Tavily / a deterministic stub and still runs offline.

API: GET https://api.aftership.com/tracking/{version}/trackings?tracking_numbers=...
Header: as-api-key. Evri's slug in AfterShip is "myhermes-uk".
"""

from __future__ import annotations

import os

import httpx

BASE = "https://api.aftership.com/tracking"


def _flatten(t: dict) -> dict:
    checkpoints = t.get("checkpoints") or []
    last = checkpoints[-1] if checkpoints else {}
    return {
        "slug": t.get("slug"),
        "tag": t.get("tag"),
        "subtag_message": t.get("subtag_message"),
        "delivered": t.get("tag") == "Delivered" or bool(t.get("shipment_delivery_date")),
        "last_checkpoint": last.get("message"),
        "last_checkpoint_time": last.get("checkpoint_time"),
        "checkpoint_count": len(checkpoints),
    }


def lookup(tracking_number: str) -> dict | None:
    """Return the parcel's AfterShip status, registering it first if needed.

    AfterShip only returns trackings it already knows, so on a miss we POST to
    create (register) the tracking — matching AfterShip's track-then-read model —
    and return whatever status it has so far. Returns None on any failure so the
    pipeline falls back to Tavily / stub.
    """
    key = os.getenv("AFTERSHIP_API_KEY")
    if not key or not tracking_number:
        return None
    version = os.getenv("AFTERSHIP_VERSION", "2026-01")
    slug = os.getenv("AFTERSHIP_SLUG", "myhermes-uk")
    headers = {"as-api-key": key, "Content-Type": "application/json"}
    base = f"{BASE}/{version}/trackings"
    try:
        with httpx.Client(timeout=15) as http:
            resp = http.get(base, params={"tracking_numbers": tracking_number}, headers=headers)
            resp.raise_for_status()
            trackings = resp.json().get("data", {}).get("trackings", [])
            if trackings:
                return _flatten(trackings[0])
            # Not tracked yet -> register it so AfterShip starts fetching carrier data.
            created = http.post(base, headers=headers, json={"tracking": {"tracking_number": tracking_number, "slug": slug}})
            if created.status_code in (200, 201):
                t = (created.json().get("data") or {}).get("tracking")
                if t:
                    return _flatten(t)
            return None
    except Exception:
        return None
