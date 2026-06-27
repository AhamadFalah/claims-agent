"""A fixed set of claims used by the snapshot test and the fixture builder.

Synthetic data — no real customer information. Mirrors the shape of the
production reference (3 loss claims across two channels).
"""

from __future__ import annotations

from app.domain.claim import Claim, ClaimType


def sample_claims() -> list[Claim]:
    return [
        Claim(
            id="c1",
            correlation_id="clm-c1",
            client_reference="REF-0001",
            channel_id="premium_a",
            channel_name="Acme Prime",
            claim_type=ClaimType.LOSS,
            tracking_number="T0AB1234",
            barcode_prefix="T0",
            order_number="ORD-1001",
            postcode="EC1A 1BB",
            cost_value=18.0,
            parcel_value=20,
            created_at="2026-04-07T09:00:00",
        ),
        Claim(
            id="c2",
            correlation_id="clm-c2",
            client_reference="REF-0002",
            channel_id="premium_a",
            channel_name="Acme Prime",
            claim_type=ClaimType.LOSS,
            tracking_number="T0CD5678",
            barcode_prefix="T0",
            order_number="ORD-1002",
            postcode="M1 1AE",
            cost_value=25.0,
            parcel_value=20,
            created_at="2026-04-07T09:05:00",
        ),
        Claim(
            id="c3",
            correlation_id="clm-c3",
            client_reference="REF-0003",
            channel_id="standard",
            channel_name="Standard Co",
            claim_type=ClaimType.LOSS,
            tracking_number="H0EF9012",
            barcode_prefix="H0",
            order_number="ORD-1003",
            postcode="LS1 4DY",
            cost_value=40.0,
            parcel_value=25,
            created_at="2026-04-07T09:10:00",
        ),
    ]
