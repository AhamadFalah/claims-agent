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


def lookup(tracking_number: str) -> dict | None:
    key = os.getenv("AFTERSHIP_API_KEY")
    if not key or not tracking_number:
        return None
    version = os.getenv("AFTERSHIP_VERSION", "2026-01")
    try:
        with httpx.Client(timeout=15) as http:
            resp = http.get(
                f"{BASE}/{version}/trackings",
                params={"tracking_numbers": tracking_number},
                headers={"as-api-key": key, "Content-Type": "application/json"},
            )
            resp.raise_for_status()
            trackings = resp.json().get("data", {}).get("trackings", [])
    except Exception:
        return None
    if not trackings:
        return None
    t = trackings[0]
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
