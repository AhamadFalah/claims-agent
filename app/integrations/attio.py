"""Attio REST v2 client — reads a claim and projects status changes back.

Used by the FastAPI agent service to:
  * hydrate a claim that n8n created in Attio (`get_claim_by_correlation_id`), and
  * push status / risk / settlement updates onto the Attio board — the live view
    the demo watches move New -> Pending -> Raised (`upsert_claim`).

Upserts by `correlation_id` (idempotent — partial, so unspecified attributes are
left untouched). No-ops cleanly when ATTIO_API_KEY is unset, so the rest of the
pipeline runs without Attio configured.
See docs/Attio Schema Design.md and docs/Integrations Reference.md.
"""

from __future__ import annotations

import os

import httpx

from app.domain.claim import Claim

BASE = "https://api.attio.com/v2"
OBJECT = os.getenv("ATTIO_CLAIM_OBJECT", "claims")


def _first(values) -> dict | None:
    return values[0] if isinstance(values, list) and values else None


def _scalar(entry: dict | None):
    """Pull a plain value out of an Attio attribute-value entry."""
    if not entry:
        return None
    if "value" in entry:
        return entry["value"]
    if entry.get("option"):
        return entry["option"].get("title")
    if entry.get("status"):
        return entry["status"].get("title")
    if "target_record_id" in entry:
        return entry["target_record_id"]
    return None


class AttioClient:
    def __init__(self, token: str | None = None):
        self.token = token or os.getenv("ATTIO_API_KEY")

    @property
    def enabled(self) -> bool:
        return bool(self.token)

    @property
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"}

    def get_claim_by_correlation_id(self, correlation_id: str) -> dict | None:
        """Return the Attio claim's values as a flat dict, or None if not found."""
        if not self.enabled:
            return None
        with httpx.Client(timeout=15) as http:
            resp = http.post(
                f"{BASE}/objects/{OBJECT}/records/query",
                headers=self._headers,
                json={"filter": {"correlation_id": correlation_id}, "limit": 1},
            )
            resp.raise_for_status()
            rows = resp.json().get("data", [])
        if not rows:
            return None
        row = rows[0]
        values = row.get("values", {})
        flat = {k: _scalar(_first(v)) for k, v in values.items()}
        flat["record_id"] = row.get("id", {}).get("record_id")
        merchant_entry = _first(values.get("merchant", []))
        if merchant_entry and merchant_entry.get("target_record_id"):
            flat["merchant_name"] = self._company_name(merchant_entry["target_record_id"])
        return flat

    def get_claim_by_tracking(self, tracking_number: str) -> dict | None:
        """Return the first Attio claim matching this tracking number as a flat dict.

        Used by outcome ingestion to resolve a claim when it is no longer in the
        agent's in-memory repo (e.g. after a restart). tracking_number is not unique
        in Attio, so the first match wins — fine for the demo.
        """
        if not self.enabled:
            return None
        with httpx.Client(timeout=15) as http:
            resp = http.post(
                f"{BASE}/objects/{OBJECT}/records/query",
                headers=self._headers,
                json={"filter": {"tracking_number": tracking_number}, "limit": 1},
            )
            resp.raise_for_status()
            rows = resp.json().get("data", [])
        if not rows:
            return None
        row = rows[0]
        values = row.get("values", {})
        flat = {k: _scalar(_first(v)) for k, v in values.items()}
        flat["record_id"] = row.get("id", {}).get("record_id")
        return flat

    def _company_name(self, record_id: str) -> str | None:
        try:
            with httpx.Client(timeout=10) as http:
                resp = http.get(
                    f"{BASE}/objects/companies/records/{record_id}",
                    headers=self._headers,
                )
                resp.raise_for_status()
                vals = resp.json().get("data", {}).get("values", {})
            return _scalar(_first(vals.get("name", [])))
        except Exception:
            return None

    def upsert_claim(self, claim: Claim) -> dict | None:
        """Project the claim's current state onto its Attio record (by correlation_id)."""
        if not self.enabled:
            return None
        values: dict = {
            "correlation_id": claim.correlation_id,
            "status": claim.status.value,
            "courier": claim.courier,
            "claim_type": claim.claim_type.value,
            "order_number": claim.order_number,
            "tracking_number": claim.tracking_number,
            "delivery_postcode": claim.postcode,
            "cost_value": claim.cost_value,
            "parcel_value": claim.parcel_value,
        }
        if claim.customer_comment:
            values["customer_comment"] = claim.customer_comment
        if claim.settlement_amount is not None:
            values["settlement_amount"] = claim.settlement_amount
        if claim.risk_score is not None:
            values["risk_score"] = claim.risk_score
        if claim.fraud_flags:
            values["fraud_flags"] = claim.fraud_flags
        with httpx.Client(timeout=15) as http:
            resp = http.put(
                f"{BASE}/objects/{OBJECT}/records",
                params={"matching_attribute": "correlation_id"},
                headers=self._headers,
                json={"data": {"values": values}},
            )
            resp.raise_for_status()
            return resp.json()
