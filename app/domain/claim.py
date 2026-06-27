"""Domain types for a claim.

Evri stays concrete; company/brand/vendor names are generalized ("channel").
See docs/State Machine & Data.md and docs/Evri File Formats.md.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Status(str, Enum):
    NEW = "New"
    PENDING = "Pending"
    RAISED = "Raised"
    ACCEPTED = "Accepted"
    REJECTED = "Rejected"
    DOR = "DOR"
    ON_HOLD = "OnHold"


class ClaimType(str, Enum):
    LOSS = "Lost"
    DAMAGE = "Damage"


class Claim(BaseModel):
    id: str
    correlation_id: str
    client_reference: str
    channel_id: str
    channel_name: str
    courier: str = "Evri"
    claim_type: ClaimType
    tracking_number: str
    barcode_prefix: str = ""  # "T0" | "H0", derived from tracking_number[:2]
    order_number: str
    postcode: str
    customer_comment: str | None = None
    cost_value: float  # internal credit value
    parcel_value: int = 0  # = channel ceiling (20|25), submitted to Evri
    product_description: str = "Loss"
    dor_letter_date: str | None = None
    status: Status = Status.NEW
    status_reason: str | None = None
    submission_ref: str | None = None
    settlement_amount: float | None = None
    risk_score: float | None = None  # fraud score, set during processing
    fraud_flags: str | None = None  # newline-separated risk signals
    created_at: str = ""  # ISO timestamp; drives CSV row ordering

    def credit_owed(self) -> float:
        """What we actually credit the client — capped at the ceiling.

        Distinct from parcel_value, which is always the ceiling we submit to Evri.
        """
        return min(self.cost_value, float(self.parcel_value))


class Channel(BaseModel):
    id: str
    name: str
    ceiling: int  # 20 or 25
    damage_allowed: bool
    barcode_prefix: str  # "T0" | "H0"
    provider: str  # "direct_mailbox" | "ticketing"
