"""Regenerate the golden snapshot fixture from the generator.

Run:  python -m tools.build_fixture
Review the resulting diff in your commit — the diff IS the contract change.
"""

from __future__ import annotations

import os

from app.generators.evri_csv import write_evri_csv
from tests.sample_claims import sample_claims

OUT = os.path.join("tests", "fixtures", "evri_golden.csv")


def main() -> None:
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    data = write_evri_csv(OUT, sample_claims())
    print(f"wrote {OUT} ({len(data)} bytes)")


if __name__ == "__main__":
    main()
