"""FastAPI agent service — the loop, exposed as HTTP for n8n to drive.

Run:  uvicorn app.main:app --reload
Each endpoint is a dumb step; n8n chains them. See docs/Technical Spec.md.
"""

from __future__ import annotations

import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.agent.decide import decide
from app.agent.enrich import enrich
from app.agent.extract import extract
from app.agent.route import recommend_model
from app.config import channel_for, load_outcomes
from app.deps import get_deps
from app.domain.claim import Claim, Status
from app.domain.state_machine import transition
from app.generators.evri_csv import generate_evri_csv
from app.integrations.dispatch_mock import dispatch

app = FastAPI(title="Autonomous Claims Operator")


def _project(deps, claim: Claim) -> None:
    deps.repo.save(claim)
    deps.repo.audit(claim, "claim.status.transition", claim.status_reason)
    deps.attio.upsert_claim(claim)


class IntakeBody(BaseModel):
    raw_email: str
    channel_id: str


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/claims/extract")
def extract_claim(body: IntakeBody) -> dict:
    deps = get_deps()
    channel = channel_for(body.channel_id)
    model_id, _ = recommend_model("Extract structured claim fields from an email")
    ex = extract(body.raw_email, model_id)
    claim_id = uuid.uuid4().hex[:12]
    claim = Claim(
        id=claim_id,
        correlation_id=f"clm-{claim_id}",
        client_reference=f"REF-{claim_id[:6].upper()}",
        channel_id=channel.id,
        channel_name=channel.name,
        claim_type=ex.claim_type,
        tracking_number=ex.tracking_number,
        order_number=ex.order_number,
        postcode=ex.postcode,
        customer_comment=ex.customer_comment,
        cost_value=ex.cost_value,
        created_at=claim_id,  # monotonic-ish for ordering in the demo
    )
    _project(deps, claim)
    return claim.model_dump()


@app.post("/claims/{claim_id}/enrich")
def enrich_claim(claim_id: str) -> dict:
    deps = get_deps()
    claim = deps.repo.get(claim_id)
    if not claim:
        raise HTTPException(404, "claim not found")
    result = enrich(claim.tracking_number, claim.postcode)
    return {"claim": claim.model_dump(), "enrichment": result}


@app.post("/claims/{claim_id}/decide")
def decide_claim(claim_id: str) -> dict:
    deps = get_deps()
    claim = deps.repo.get(claim_id)
    if not claim:
        raise HTTPException(404, "claim not found")
    channel = channel_for(claim.channel_id)
    new_status = decide(claim, channel)
    transition(claim, new_status, reason=claim.status_reason)
    _project(deps, claim)
    return claim.model_dump()


@app.post("/batches/generate")
def generate_batch() -> dict:
    deps = get_deps()
    pending = [c for c in deps.repo.all() if c.status == Status.PENDING]
    if not pending:
        return {"count": 0, "csv": ""}
    csv_bytes = generate_evri_csv(pending)
    return {
        "count": len(pending),
        "claim_ids": [c.id for c in pending],
        "csv": csv_bytes.decode("utf-8"),
    }


@app.post("/batches/dispatch")
def dispatch_batch() -> dict:
    deps = get_deps()
    pending = [c for c in deps.repo.all() if c.status == Status.PENDING]
    if not pending:
        return {"count": 0}
    csv_bytes = generate_evri_csv(pending)
    result = dispatch(csv_bytes, pending[0].channel_name)
    for claim in pending:
        claim.submission_ref = result["submission_ref"]
        transition(claim, Status.RAISED, reason=f"Batch {result['file_sha256'][:8]}")
        _project(deps, claim)
    return {"count": len(pending), **result}


class OutcomeBody(BaseModel):
    barcode: str
    claim_status: str  # e.g. "Accepted (DA1)", "SP1", "Rejected (OOT)"
    settlement_amount: float | None = None


@app.post("/outcomes/ingest")
def ingest_outcome(body: OutcomeBody) -> dict:
    deps = get_deps()
    claim = deps.repo.by_barcode(body.barcode)
    if not claim:
        raise HTTPException(404, "no claim for barcode")
    if claim.status in (Status.ACCEPTED, Status.REJECTED):
        return {"ignored": True, "reason": "terminal", "status": claim.status.value}

    cfg = load_outcomes()
    code = _parse_code(body.claim_status)
    if code in cfg["dor_codes"]:
        transition(claim, Status.DOR, reason=code)
    elif code in cfg["accept_codes"]:
        transition(claim, Status.ACCEPTED, reason=code)
        claim.settlement_amount = body.settlement_amount or float(claim.parcel_value)
    else:
        reason = cfg["reject_reasons"].get(code, code)
        transition(claim, Status.REJECTED, reason=reason)
    _project(deps, claim)
    return claim.model_dump()


def _parse_code(claim_status: str) -> str:
    if "(" in claim_status and ")" in claim_status:
        return claim_status.split("(")[1].split(")")[0].strip()
    return claim_status.strip()
