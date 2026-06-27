"""Claim status state machine. The only place status changes.

See docs/State Machine & Data.md for the contract.
"""

from __future__ import annotations

from .claim import Claim, Status


class InvalidTransition(Exception):
    pass


ALLOWED: dict[Status, set[Status]] = {
    Status.NEW: {Status.PENDING, Status.REJECTED, Status.ON_HOLD},
    Status.PENDING: {Status.RAISED, Status.REJECTED, Status.ON_HOLD},
    Status.RAISED: {Status.ACCEPTED, Status.REJECTED, Status.DOR, Status.ON_HOLD},
    Status.DOR: {Status.RAISED, Status.REJECTED, Status.ON_HOLD},
    Status.ON_HOLD: {
        Status.NEW,
        Status.PENDING,
        Status.RAISED,
        Status.DOR,
        Status.REJECTED,
    },
    Status.ACCEPTED: set(),  # terminal
    Status.REJECTED: set(),  # terminal
}


def can_transition(current: Status, new: Status) -> bool:
    return new in ALLOWED[current]


def transition(claim: Claim, new: Status, *, reason: str | None = None) -> Claim:
    """Validate and apply a status transition.

    In the full system this also writes an audit-log row in the same DB
    transaction and projects to Attio. Here we keep it pure so it is trivially
    testable; callers (workflows) handle persistence + projection.
    """
    if claim.status in (Status.ACCEPTED, Status.REJECTED) and claim.status == new:
        return claim  # idempotent no-op on terminal
    if not can_transition(claim.status, new):
        raise InvalidTransition(f"Cannot move {claim.id} from {claim.status} to {new}")
    claim.status = new
    claim.status_reason = reason
    return claim
