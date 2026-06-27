"""Deterministic fraud / risk scoring for a claim.

Not an LLM — a small, explainable heuristic so the demo is reproducible. Produces
a 0-100 score plus human-readable flags, which the agent projects onto the Attio
claim (`risk_score`, `fraud_flags`).
"""

from __future__ import annotations

from app.domain.claim import Claim


def assess_risk(claim: Claim, enrichment: dict) -> tuple[int, list[str]]:
    """Return (risk_score 0-100, list of flag strings)."""
    flags: list[str] = []

    if not enrichment.get("postcode_valid", bool(claim.postcode)):
        flags.append("missing_or_invalid_postcode")

    tn = (claim.tracking_number or "").upper()
    if not (tn.startswith("T0") or tn.startswith("H0")):
        flags.append("tracking_prefix_unrecognised")

    if claim.cost_value <= 0:
        flags.append("no_stated_cost_value")
    elif claim.cost_value > 100:
        flags.append("high_stated_value")

    # Stated cost far above the ceiling can indicate value inflation.
    if claim.parcel_value and claim.cost_value > float(claim.parcel_value) * 3:
        flags.append("stated_cost_exceeds_3x_ceiling")

    score = min(100, len(flags) * 20)
    return score, flags
