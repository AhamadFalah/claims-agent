"""Step 2 — verify a claim against the carrier's real tracking status.

Priority: AfterShip (real carrier data) -> Tavily (web) -> deterministic stub.
Returns a verdict the agent uses to gate the claim:
  contradicted = carrier shows Delivered          -> reject
  in_progress  = still moving / out for delivery  -> hold (too early to claim)
  supported    = exception / failed / never scanned -> proceed to submit
  unknown      = no signal (offline)              -> proceed (offline-safe default)
"""

from __future__ import annotations

import os

from app.integrations.aftership import lookup as aftership_lookup

_IN_PROGRESS = {"InTransit", "OutForDelivery", "AvailableForPickup"}
_SUPPORTED = {"Exception", "AttemptFail", "Expired", "InfoReceived", "Pending"}


def _verdict(tag: str | None, delivered: bool) -> str:
    if delivered:
        return "contradicted"
    if tag in _IN_PROGRESS:
        return "in_progress"
    if tag in _SUPPORTED:
        return "supported"
    return "unknown"


def enrich(tracking_number: str, postcode: str) -> dict:
    # 1) AfterShip — real carrier verification
    track = aftership_lookup(tracking_number)
    if track:
        summary = (
            f"AfterShip [{track.get('slug')}]: {track.get('tag')} — "
            f"{track.get('subtag_message') or track.get('last_checkpoint') or ''}"
        ).strip()
        return {
            "source": "aftership",
            "tracking_summary": summary,
            "tag": track.get("tag"),
            "delivered": track.get("delivered", False),
            "verdict": _verdict(track.get("tag"), track.get("delivered", False)),
            "last_checkpoint": track.get("last_checkpoint"),
            "sources": [],
            "postcode_valid": bool(postcode),
        }

    # 2) Tavily — web fallback
    if os.getenv("TAVILY_API_KEY"):
        try:
            from tavily import TavilyClient

            client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
            r = client.search(
                query=f"Evri parcel {tracking_number} tracking status lost not delivered",
                max_results=3,
                include_answer=True,
            )
            return {
                "source": "tavily",
                "tracking_summary": r.get("answer", ""),
                "tag": None,
                "delivered": False,
                "verdict": "unknown",
                "sources": [x["url"] for x in r.get("results", [])],
                "postcode_valid": bool(postcode),
            }
        except Exception:
            pass

    # 3) Deterministic stub (offline-safe)
    return {
        "source": "stub",
        "tracking_summary": f"(stub) No live lookup. Parcel {tracking_number} to "
        f"{postcode or 'unknown postcode'} treated as not delivered.",
        "tag": None,
        "delivered": False,
        "verdict": "unknown",
        "sources": [],
        "postcode_valid": bool(postcode),
    }
