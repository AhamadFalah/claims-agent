"""Attio REST v2 client — projects each claim as a record + status pipeline.

Upserts by `correlation_id` (idempotent). No-ops cleanly when ATTIO_API_KEY is
unset, so the rest of the pipeline runs without Attio configured.
See docs/Integrations Reference.md.
"""

from __future__ import annotations

import os

import httpx

from app.domain.claim import Claim

BASE = "https://api.attio.com/v2"
OBJECT = os.getenv("ATTIO_CLAIM_OBJECT", "claims")


class AttioClient:
    def __init__(self, token: str | None = None):
        self.token = token or os.getenv("ATTIO_API_KEY")

    @property
    def enabled(self) -> bool:
        return bool(self.token)

    def upsert_claim(self, claim: Claim) -> dict | None:
        if not self.enabled:
            return None
        payload = {
            "data": {
                "values": {
                    "correlation_id": claim.correlation_id,
                    "order_number": claim.order_number,
                    "tracking_number": claim.tracking_number,
                    "channel": claim.channel_name,
                    "claim_type": claim.claim_type.value,
                    "parcel_value": claim.parcel_value,
                    "status": claim.status.value,
                    "settlement_amount": claim.settlement_amount,
                }
            }
        }
        with httpx.Client(timeout=15) as http:
            resp = http.put(
                f"{BASE}/objects/{OBJECT}/records",
                params={"matching_attribute": "correlation_id"},
                headers={"Authorization": f"Bearer {self.token}"},
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()
