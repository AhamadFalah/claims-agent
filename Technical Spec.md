# Technical Spec

Build-level spec for the hackathon MVP. Evri stays concrete; company/brand/vendor names are generalized ("channel", "OMS"). See [[Evri File Formats]], [[State Machine & Data]], [[Integrations Reference]] for the deep reference pulled from the production repo.

## System topology
```
n8n (orchestrator)
   │  POST /webhook/claim-intake        <- seeded email/form JSON
   v
FastAPI agent service  (Python 3.11, httpx, pydantic v2)
   |- POST /claims/extract     -> Gemini (structured output)
   |- POST /claims/{id}/enrich -> Tavily
   |- POST /claims/{id}/decide -> deterministic eligibility
   |- POST /batches/generate   -> byte-exact CSV (pure fn) + snapshot guard
   |- POST /batches/{id}/dispatch  -> MOCK (writes file, no SMTP)
   |- POST /outcomes/ingest    -> state machine + DOR trigger
   |
   |- SQLite (SQLAlchemy 2.x)  <- source of truth for state
   |- Attio REST v2            <- projection: Claim records + status pipeline (live UI)
```

Two non-negotiable rules carried from the production repo:
1. **All status changes go through one `transition()`** — never assign `claim.status` directly.
2. **The CSV generator is a pure function guarded by a byte-equality snapshot test.**

## Repo layout (fresh public repo)
```
claims-agent/
  app/
    main.py                 # FastAPI app + routes
    deps.py                 # Deps container (settings, clients, repos)
    domain/
      claim.py              # Pydantic models + Status enum
      state_machine.py      # ALLOWED_TRANSITIONS + transition()
    agent/
      extract.py            # Gemini structured extraction
      enrich.py             # Tavily lookups
      decide.py             # eligibility rules
      route.py              # Minima model routing
    generators/
      evri_csv.py           # PORTED, byte-exact. Do not touch the header.
    integrations/
      attio.py              # REST v2 client
      dispatch_mock.py      # fake send
    persistence/
      db.py, models.py, repo.py
    config/
      channels.yaml, outcomes.yaml
  tests/
    fixtures/evri_apr07_real.csv     # the golden file (656 bytes)
    test_evri_csv_snapshot.py        # byte-equality
  n8n/claims-loop.json               # exported workflow
  README.md
```

## Domain model
```python
from enum import Enum
from pydantic import BaseModel

class Status(str, Enum):
    NEW="New"; PENDING="Pending"; RAISED="Raised"
    ACCEPTED="Accepted"; REJECTED="Rejected"; DOR="DOR"; ON_HOLD="OnHold"

class ClaimType(str, Enum):
    LOSS="Lost"; DAMAGE="Damage"

class Claim(BaseModel):
    id: str
    correlation_id: str
    channel_id: str               # generalized "brand"
    channel_name: str
    courier: str = "Evri"
    claim_type: ClaimType
    tracking_number: str
    barcode_prefix: str           # "T0" | "H0", = tracking[:2]
    order_number: str
    postcode: str
    customer_comment: str | None = None
    cost_value: float             # internal credit value
    parcel_value: int             # = channel ceiling (20|25), submitted to Evri
    product_description: str = "Loss"
    dor_letter_date: str | None = None
    status: Status = Status.NEW
    status_reason: str | None = None
    submission_ref: str | None = None
    settlement_amount: float | None = None
    created_at: str               # ISO; drives CSV row ordering
```

Pricing rule (critical): submit at the **ceiling** -> `parcel_value = ceiling` (integer). The credit owed to the client is a *separate* number = `min(cost_value, ceiling)`. The system never writes the operator-only `Amount` field.

## Step 1 - Gemini extraction (structured output)
```python
from google import genai

class Extracted(BaseModel):
    order_number: str
    tracking_number: str
    postcode: str
    claim_type: ClaimType
    cost_value: float
    customer_comment: str

def extract(raw_email: str, model_id: str) -> Extracted:
    client = genai.Client()
    resp = client.models.generate_content(
        model=model_id,                       # from Minima, e.g. gemini-2.5-flash
        contents=f"Extract the claim fields from this email:\n\n{raw_email}",
        config={
            "response_mime_type": "application/json",
            "response_schema": Extracted,
            "temperature": 0,
        },
    )
    return Extracted.model_validate_json(resp.text)
```
LLM does judgment (which courier, loss vs damage, which number is tracking). It never formats output bytes.

## Step 2 - Tavily enrichment
```python
from tavily import TavilyClient

def enrich(claim, tavily: TavilyClient):
    r = tavily.search(
        query=f"Evri parcel {claim.tracking_number} tracking status lost",
        max_results=3, include_answer=True,
    )
    return {"tracking_summary": r["answer"], "sources": [x["url"] for x in r["results"]]}
```
Replaces the live OMS lookup for the demo. Cache to fixtures so the demo survives bad wifi.

## Step 3 - Eligibility (deterministic, not LLM)
```python
def decide(claim, channel) -> Status:
    if claim.claim_type == ClaimType.DAMAGE and not channel["damage_allowed"]:
        claim.status_reason = "Damage claim not covered for this channel"
        return Status.REJECTED
    claim.parcel_value = channel["ceiling"]        # 20 or 25, integer
    claim.barcode_prefix = claim.tracking_number[:2]
    return Status.PENDING
```

## Step 4 - Byte-exact generator (load-bearing)
Ported verbatim. Full byte rules in [[Evri File Formats]].
```python
HEADER = [
    " CLIENT REFERNCE NO", "BRAND NAME", "HERMES BARCODE", "ORDER NO",
    "CUSTOMER NAME", "POSTCODE", "DOR LETTER DATE", "CLIENT OR CUSTOMER COMMENTS",
    "PARCEL VALUE", "PRODUCT CATEGORY", "PRODUCT DESCRIPTION", "CARRIAGE",
    "LOST OR DAMAGED",
]

def _clean(v: str) -> str:
    return v.replace(",", " ").replace('"', "").replace("\n", " ").replace("\r", "")

def _row(c) -> list[str]:
    is_loss = c.claim_type == ClaimType.LOSS
    return [
        c.correlation_id, c.channel_name, c.tracking_number, c.order_number,
        "Customer",                              # literal
        c.postcode,
        c.dor_letter_date or "",                 # populated only on DOR resubmit
        _clean(c.customer_comment or ("Consignment lost or Tracking not update"
                                      if is_loss else "Item arrived damaged")),
        str(c.parcel_value),                     # ceiling, integer
        "Other",                                 # literal
        "Loss" if is_loss else c.product_description,
        "",                                      # carriage always empty
        "Lost Claim" if is_loss else "Damage Claim",
    ]

def generate_evri_csv(claims: list) -> bytes:
    rows = sorted(claims, key=lambda c: (c.channel_name, c.created_at))
    lines = [",".join(HEADER)] + [",".join(_row(c)) for c in rows]
    text = "\r\n".join(lines) + "\r\n"           # trailing CRLF
    return text.encode("utf-8")                  # no BOM; caller writes "wb"
```
Snapshot test (the technical-complexity money shot):
```python
def test_apr07_byte_for_byte():
    out = generate_evri_csv(load_fixture_claims())
    assert out == open("tests/fixtures/evri_apr07_real.csv", "rb").read()
    assert out[:20] == b" CLIENT REFERNCE NO,"   # leading space + typo locked
```

## Step 5 - State machine
Full table + DB schema in [[State Machine & Data]].
```python
def transition(claim, new, *, reason=None, repo, attio):
    if new not in ALLOWED[claim.status]:
        raise InvalidTransition(f"{claim.status} -> {new}")
    claim.status, claim.status_reason = new, reason
    with repo.db.begin():                 # audit + state in one tx
        repo.save(claim)
        repo.audit(claim, new, reason)
    attio.upsert_claim(claim)             # projection after commit
    return claim
```

## Step 6 - Outcome ingestion (resolve)
```python
DOR_CODES = {"SP1","SP3","SP4","P01"}
def apply_outcome(row, repo, attio):
    claim = repo.by_barcode(row["HERMES BARCODE"])
    if claim.status in (Status.ACCEPTED, Status.REJECTED):
        log.warning("terminal.outcome.ignored"); return        # log & ignore
    code = parse_code(row["Claim Status"])
    if code in DOR_CODES:   transition(claim, Status.DOR, reason=code, repo=repo, attio=attio)
    elif code == "DA1":     transition(claim, Status.ACCEPTED, repo=repo, attio=attio)
    else:                   transition(claim, Status.REJECTED, reason=code, repo=repo, attio=attio)
```

## Attio integration (REST v2)
Custom object `claim`; `status` attribute = pipeline. Upsert by `correlation_id` (idempotent).
```python
class AttioClient:
    BASE = "https://api.attio.com/v2"
    def upsert_claim(self, c):
        return self._http.put(
            f"{self.BASE}/objects/claims/records",
            params={"matching_attribute": "correlation_id"},
            headers={"Authorization": f"Bearer {self.token}"},
            json={"data": {"values": {
                "correlation_id": c.correlation_id,
                "order_number": c.order_number,
                "tracking_number": c.tracking_number,
                "claim_type": c.claim_type.value,
                "parcel_value": c.parcel_value,
                "status": c.status.value,
                "settlement_amount": c.settlement_amount,
            }}},
        )
```
Live status changes here are what judges watch move on the Attio board. If Attio Workflows are fiddly, n8n drives the loop and Attio is pure projection + UI - still satisfies "built on Attio".

## n8n orchestration
Single workflow exported to `n8n/claims-loop.json`:
```
Webhook(claim-intake)
  -> HTTP POST /claims/extract
  -> HTTP POST /claims/{id}/enrich
  -> HTTP POST /claims/{id}/decide
  -> IF status == Rejected -> end (logged)
  -> HTTP POST /batches/generate
  -> HTTP POST /batches/{id}/dispatch
  -> Wait / Manual trigger (demo button)
  -> HTTP POST /outcomes/ingest   (seeded outcome fixture)
```
n8n owns the autonomous framing (trigger + chaining + per-node retry); FastAPI owns logic.

## Minima routing (side prize)
```python
rec = minima.recommend("Extract structured claim fields from a courier email",
                       cost_quality_tradeoff=3)
model_id = rec.recommended_model.model_id     # feed into extract()
minima.feedback(rec.recommendation_id, model_id, "success",
                quality_score=0.95, input_tokens=..., output_tokens=...)
```

## Demo-safety engineering
- **Determinism:** temperature 0; seeded fixtures for Tavily + outcomes -> identical, offline-safe runs.
- **Idempotency:** Attio upsert by `correlation_id`; outcome ingest keyed by `(claim_id, code)`; n8n re-runs are no-ops.
- **Mock dispatch:** writes CSV to `data/batches/<sha256>.csv`, returns a fake ref `260428-014769` so `Raised` has real-looking data.
- **Never break the snapshot test** - wire into CI; green check + Aikido both visible to judges.

Related: [[Architecture]] · [[Evri File Formats]] · [[State Machine & Data]] · [[Integrations Reference]] · [[Build Plan & Timeline]]
