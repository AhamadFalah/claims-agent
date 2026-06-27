from __future__ import annotations

import pytest

from app.domain.claim import Status
from app.domain.state_machine import InvalidTransition, transition
from tests.sample_claims import sample_claims


def _claim():
    return sample_claims()[0]


def test_valid_path_to_accepted():
    c = _claim()
    transition(c, Status.PENDING)
    transition(c, Status.RAISED)
    transition(c, Status.ACCEPTED)
    assert c.status == Status.ACCEPTED


def test_terminal_is_frozen():
    c = _claim()
    transition(c, Status.PENDING)
    transition(c, Status.RAISED)
    transition(c, Status.REJECTED, reason="OOT")
    with pytest.raises(InvalidTransition):
        transition(c, Status.ACCEPTED)


def test_illegal_jump_rejected():
    c = _claim()
    with pytest.raises(InvalidTransition):
        transition(c, Status.ACCEPTED)  # NEW -> ACCEPTED is not allowed


def test_dor_loop():
    c = _claim()
    transition(c, Status.PENDING)
    transition(c, Status.RAISED)
    transition(c, Status.DOR, reason="SP1")
    transition(c, Status.RAISED)  # signed PDF received -> resubmitted
    assert c.status == Status.RAISED
