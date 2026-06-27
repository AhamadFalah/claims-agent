"""Minimal in-memory claim store for the MVP.

Swap for SQLite/SQLAlchemy later (see docs/State Machine & Data.md for the schema).
Kept dependency-free so the repo runs out of the box.
"""

from __future__ import annotations

from app.domain.claim import Claim


class ClaimRepo:
    def __init__(self) -> None:
        self._by_id: dict[str, Claim] = {}
        self._audit: list[dict] = []

    def save(self, claim: Claim) -> Claim:
        self._by_id[claim.id] = claim
        return claim

    def get(self, claim_id: str) -> Claim | None:
        return self._by_id.get(claim_id)

    def by_barcode(self, barcode: str) -> Claim | None:
        for c in self._by_id.values():
            if c.tracking_number == barcode:
                return c
        return None

    def all(self) -> list[Claim]:
        return list(self._by_id.values())

    def audit(self, claim: Claim, action: str, reason: str | None) -> None:
        self._audit.append(
            {
                "correlation_id": claim.correlation_id,
                "action": action,
                "status": claim.status.value,
                "reason": reason,
            }
        )

    def audit_log(self) -> list[dict]:
        return list(self._audit)
