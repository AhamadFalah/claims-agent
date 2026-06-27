"""Step 3 — deterministic eligibility decision. Not an LLM.

Applies channel rules: damage only on eligible channels, price at the ceiling,
derive the barcode prefix.
"""

from __future__ import annotations

from app.domain.claim import Claim, ClaimType, Status


def decide(claim: Claim, channel) -> Status:
    if claim.claim_type == ClaimType.DAMAGE and not channel.damage_allowed:
        claim.status_reason = "Damage claim not covered for this channel"
        return Status.REJECTED
    claim.parcel_value = channel.ceiling  # ceiling as integer, not cost_value
    claim.barcode_prefix = claim.tracking_number[:2].upper()
    if claim.claim_type == ClaimType.LOSS:
        claim.product_description = "Loss"
    return Status.PENDING
