"""Step 1 — extract a structured claim from a free-text email using Gemini.

Falls back to a deterministic regex/heuristic extractor when no GEMINI_API_KEY is
set, so the demo runs offline. The LLM does judgment (loss vs damage, which number
is tracking); it never formats output bytes.
"""

from __future__ import annotations

import os
import re

from pydantic import BaseModel

from app.domain.claim import ClaimType


class Extracted(BaseModel):
    order_number: str
    tracking_number: str
    postcode: str
    claim_type: ClaimType
    cost_value: float
    customer_comment: str


_UK_POSTCODE = re.compile(r"\b([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})\b", re.I)
_TRACKING = re.compile(r"\b([TH]0[A-Z0-9]{6,})\b", re.I)
_ORDER = re.compile(r"\b((?:ORD|FB|GB)[-\s]?[A-Z0-9-]{3,})\b", re.I)
_MONEY = re.compile(r"£\s*(\d+(?:\.\d{1,2})?)")


def _heuristic(raw: str) -> Extracted:
    pc = _UK_POSTCODE.search(raw)
    tn = _TRACKING.search(raw)
    on = _ORDER.search(raw)
    money = _MONEY.search(raw)
    is_damage = bool(re.search(r"damag|broken|smashed|crushed", raw, re.I))
    return Extracted(
        order_number=(on.group(1).strip() if on else "UNKNOWN"),
        tracking_number=(tn.group(1).upper() if tn else "T0UNKNOWN"),
        postcode=(pc.group(1).upper() if pc else ""),
        claim_type=ClaimType.DAMAGE if is_damage else ClaimType.LOSS,
        cost_value=(float(money.group(1)) if money else 0.0),
        customer_comment=raw.strip().split("\n")[0][:120],
    )


def extract(raw_email: str, model_id: str | None = None) -> Extracted:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return _heuristic(raw_email)
    try:
        from google import genai  # imported lazily so the repo runs without the dep

        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(
            model=model_id or os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            contents=f"Extract the claim fields from this email:\n\n{raw_email}",
            config={
                "response_mime_type": "application/json",
                "response_schema": Extracted,
                "temperature": 0,
            },
        )
        return Extracted.model_validate_json(resp.text)
    except Exception:
        return _heuristic(raw_email)
