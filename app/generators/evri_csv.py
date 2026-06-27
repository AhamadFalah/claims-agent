"""Byte-exact Evri submission CSV generator.

This is the load-bearing part of the system. The output must match Evri's parser
exactly: 13 columns, exact headers (including the deliberate `REFERNCE` typo and a
leading space on column 1), UTF-8 without BOM, CRLF line endings including a
trailing newline, and never-quoted fields.

Do not "fix" the header typo — Evri's parser keys off the exact string.
See docs/Evri File Formats.md.
"""

from __future__ import annotations

from collections.abc import Iterable

from app.domain.claim import Claim, ClaimType

HEADER: list[str] = [
    " CLIENT REFERNCE NO",  # leading space + REFERNCE typo are intentional
    "BRAND NAME",
    "HERMES BARCODE",
    "ORDER NO",
    "CUSTOMER NAME",
    "POSTCODE",
    "DOR LETTER DATE",
    "CLIENT OR CUSTOMER COMMENTS",
    "PARCEL VALUE",
    "PRODUCT CATEGORY",
    "PRODUCT DESCRIPTION",
    "CARRIAGE",
    "LOST OR DAMAGED",
]

LOSS_COMMENT = "Consignment lost or Tracking not update"
DAMAGE_COMMENT = "Item arrived damaged"


def _clean(value: str) -> str:
    """Strip characters that would break the unquoted CSV."""
    return (
        value.replace(",", " ")
        .replace('"', "")
        .replace("\n", " ")
        .replace("\r", "")
    )


def _row(c: Claim) -> list[str]:
    is_loss = c.claim_type == ClaimType.LOSS
    comment = c.customer_comment or (LOSS_COMMENT if is_loss else DAMAGE_COMMENT)
    return [
        c.client_reference,
        c.channel_name,
        c.tracking_number,
        c.order_number,
        "Customer",  # literal — never the real name
        c.postcode,
        c.dor_letter_date or "",  # populated only on DOR resubmission
        _clean(comment),
        str(c.parcel_value),  # the ceiling, as integer
        "Other",  # literal
        "Loss" if is_loss else c.product_description,
        "",  # carriage always empty
        "Lost Claim" if is_loss else "Damage Claim",
    ]


def generate_evri_csv(claims: Iterable[Claim]) -> bytes:
    """Return the submission CSV as bytes. Pure: same input -> same bytes.

    Rows are ordered by channel name, then claim insertion time.
    """
    ordered = sorted(claims, key=lambda c: (c.channel_name, c.created_at))
    lines = [",".join(HEADER)] + [",".join(_row(c)) for c in ordered]
    text = "\r\n".join(lines) + "\r\n"  # trailing CRLF on the last line too
    return text.encode("utf-8")  # no BOM


def write_evri_csv(path: str, claims: Iterable[Claim]) -> bytes:
    data = generate_evri_csv(claims)
    with open(path, "wb") as f:  # binary mode — never text mode
        f.write(data)
    return data
