"""FastAPI agent service — the loop, exposed as HTTP for n8n to drive.

Run:  uvicorn app.main:app --reload
Each endpoint is a dumb step; n8n chains them. See docs/Technical Spec.md.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import Body, FastAPI, HTTPException
from pydantic import BaseModel

from app.agent.decide import decide
from app.agent.enrich import enrich
from app.agent.extract import extract
from app.agent.risk import assess_risk
from app.agent.route import recommend_model
from app.config import channel_for, load_outcomes
from app.deps import get_deps
from app.domain.claim import Channel, Claim, ClaimType, Status
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


class ProcessBody(BaseModel):
    """Optional claim fields. If omitted, the claim is read from Attio by correlation_id."""

    order_number: str | None = None
    courier: str | None = None
    claim_type: str | None = None
    tracking_number: str | None = None
    delivery_postcode: str | None = None
    postcode: str | None = None
    cost_value: float | None = None
    parcel_value: int | None = None
    customer_comment: str | None = None
    merchant_name: str | None = None
    channel_name: str | None = None


def _build_claim(correlation_id: str, data: dict) -> Claim:
    tracking = str(data.get("tracking_number") or "T0UNKNOWN").upper()
    return Claim(
        id=correlation_id,
        correlation_id=correlation_id,
        client_reference=f"REF-{correlation_id[:8].upper()}",
        channel_id="evri",
        channel_name=str(data.get("merchant_name") or data.get("channel_name") or "Evri Merchant"),
        courier=str(data.get("courier") or "Evri"),
        claim_type=ClaimType(data.get("claim_type") or "Lost"),
        tracking_number=tracking,
        order_number=str(data.get("order_number") or "UNKNOWN"),
        postcode=str(data.get("delivery_postcode") or data.get("postcode") or ""),
        customer_comment=data.get("customer_comment"),
        cost_value=float(data.get("cost_value") or 0),
        parcel_value=int(data.get("parcel_value") or 20),
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def _channel_for_claim(claim: Claim) -> Channel:
    """Synthetic channel derived from the claim (ceiling = parcel_value set upstream)."""
    return Channel(
        id="evri",
        name=claim.channel_name,
        ceiling=claim.parcel_value or 20,
        damage_allowed=True,
        barcode_prefix=(claim.tracking_number[:2] or "T0"),
        provider="direct_mailbox",
    )


def _result(correlation_id: str, claim: Claim, verdict: str | None, flags: list[str], steps: list[dict]) -> dict:
    out = {
        "correlation_id": correlation_id,
        "status": claim.status.value,
        "verdict": verdict,
        "reason": claim.status_reason,
        "parcel_value": claim.parcel_value,
        "cost_value": claim.cost_value,
        "credit_owed": claim.credit_owed(),
        "risk_score": claim.risk_score,
        "fraud_flags": flags,
        "steps": steps,
    }
    if claim.submission_ref:
        out["submission_ref"] = claim.submission_ref
    return out


@app.post("/claims/{correlation_id}/process")
def process_claim(correlation_id: str, body: ProcessBody | None = Body(default=None)) -> dict:
    """Autonomous Evri loop for one claim: enrich -> risk -> decide -> generate -> dispatch.

    Claim data comes from the request body if provided, else is read from Attio by
    correlation_id. Each status change is projected onto the Attio board.
    """
    deps = get_deps()

    data = body.model_dump(exclude_none=True) if body else {}
    if not data.get("tracking_number"):
        fetched = deps.attio.get_claim_by_correlation_id(correlation_id)
        if fetched:
            data = {**fetched, **data}
    if not data:
        raise HTTPException(
            404,
            f"No claim data for {correlation_id}. POST the claim fields, or set "
            "ATTIO_API_KEY so the service can read it from Attio.",
        )

    courier = str(data.get("courier") or "Evri")
    if courier.strip().lower() != "evri":
        raise HTTPException(422, f"Phase 1 processes Evri only; got courier '{courier}'.")

    claim = _build_claim(correlation_id, data)
    deps.repo.save(claim)
    steps: list[dict] = []

    # Enrich/verify against real carrier tracking (AfterShip) + deterministic risk score
    enrichment = enrich(claim.tracking_number, claim.postcode)
    claim.risk_score, flags = assess_risk(claim, enrichment)
    carrier_line = f"carrier:{enrichment.get('tag') or enrichment.get('source')} ({enrichment.get('verdict')})"
    claim.fraud_flags = "\n".join([carrier_line, *flags])
    steps.append(
        {
            "step": "enrich",
            "source": enrichment.get("source"),
            "tag": enrichment.get("tag"),
            "verdict": enrichment.get("verdict"),
            "tracking_summary": enrichment.get("tracking_summary"),
            "risk_score": claim.risk_score,
            "fraud_flags": flags,
        }
    )

    # Carrier-data verification gate (before eligibility):
    #   Delivered    -> reject (not eligible)
    #   in transit   -> hold (too early to claim)
    verdict = enrichment.get("verdict")
    if enrichment.get("delivered"):
        transition(claim, Status.REJECTED, reason="Carrier tracking shows Delivered — not eligible")
        _project(deps, claim)
        steps.append({"step": "verify", "status": claim.status.value, "reason": claim.status_reason})
        return _result(correlation_id, claim, verdict, flags, steps)
    if verdict == "in_progress":
        transition(claim, Status.ON_HOLD, reason="Parcel still in transit — too early to claim")
        _project(deps, claim)
        steps.append({"step": "verify", "status": claim.status.value, "reason": claim.status_reason})
        return _result(correlation_id, claim, verdict, flags, steps)

    # Eligibility decision: New -> Pending (or Rejected by channel rules)
    channel = _channel_for_claim(claim)
    new_status = decide(claim, channel)
    transition(claim, new_status, reason=claim.status_reason)
    _project(deps, claim)
    steps.append({"step": "decide", "status": claim.status.value, "reason": claim.status_reason})

    if claim.status == Status.REJECTED:
        return _result(correlation_id, claim, verdict, flags, steps)

    # Generate byte-exact CSV + mock dispatch: Pending -> Raised
    csv_bytes = generate_evri_csv([claim])
    result = dispatch(csv_bytes, claim.channel_name)
    claim.submission_ref = result["submission_ref"]
    transition(claim, Status.RAISED, reason=f"Batch {result['file_sha256'][:8]}")
    _project(deps, claim)
    steps.append(
        {
            "step": "dispatch",
            "status": claim.status.value,
            "submission_ref": claim.submission_ref,
            "file_sha256": result["file_sha256"],
        }
    )

    return _result(correlation_id, claim, verdict, flags, steps)


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
