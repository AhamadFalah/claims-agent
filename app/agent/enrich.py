"""Step 2 — enrich a claim with Tavily (tracking status / address sanity).

Replaces the live OMS lookup for the demo. Returns a cached/stub result when no
TAVILY_API_KEY is set so the demo survives bad wifi.
"""

from __future__ import annotations

import os


def enrich(tracking_number: str, postcode: str) -> dict:
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return {
            "tracking_summary": f"(stub) No live lookup. Parcel {tracking_number} "
            f"to {postcode or 'unknown postcode'} treated as not delivered.",
            "sources": [],
            "postcode_valid": bool(postcode),
        }
    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=api_key)
        r = client.search(
            query=f"Evri parcel {tracking_number} tracking status lost not delivered",
            max_results=3,
            include_answer=True,
        )
        return {
            "tracking_summary": r.get("answer", ""),
            "sources": [x["url"] for x in r.get("results", [])],
            "postcode_valid": bool(postcode),
        }
    except Exception as e:
        return {"tracking_summary": f"(error) {e}", "sources": [], "postcode_valid": bool(postcode)}
