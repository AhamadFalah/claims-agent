"""Byte-exact snapshot test — the contract with Evri's parser.

If this fails after an intentional format change, regenerate the fixture with
`python -m tools.build_fixture` and review the diff in the commit. Never silently
regenerate — the diff is the contract change.
"""

from __future__ import annotations

import os

from app.generators.evri_csv import generate_evri_csv
from tests.sample_claims import sample_claims

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "evri_golden.csv")


def test_golden_byte_for_byte():
    out = generate_evri_csv(sample_claims())
    with open(FIXTURE, "rb") as f:
        expected = f.read()
    assert out == expected


def test_header_is_exact():
    out = generate_evri_csv(sample_claims())
    assert out[:20] == b" CLIENT REFERNCE NO,"  # leading space + REFERNCE typo


def test_crlf_and_trailing_newline():
    out = generate_evri_csv(sample_claims())
    assert out.endswith(b"\r\n")
    assert b"\r\n" in out
    assert b"\r\r\n" not in out  # no double-CR (text-mode bug)


def test_no_bom():
    out = generate_evri_csv(sample_claims())
    assert not out.startswith(b"\xef\xbb\xbf")


def test_thirteen_columns():
    out = generate_evri_csv(sample_claims())
    header = out.split(b"\r\n")[0]
    assert header.count(b",") == 12  # 13 columns -> 12 commas
