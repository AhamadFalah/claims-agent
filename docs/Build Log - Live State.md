# Build Log — Live State

> What's actually stood up (Attio + n8n + agent service), what's verified, and what's still pending. Companion to [[Technical Spec]], [[Architecture]], [[Attio Schema Design]], [[Integrations Reference]].
> Snapshot: 2026-06-27.

## TL;DR
The Attio data model, the **live** n8n `claims-loop` workflow, and the FastAPI `/process` agent route are built and verified end-to-end. Remaining: deploy the agent publicly, point n8n at it, and add **AfterShip** for real tracking verification.

---

## What's built & verified

### Attio — workspace *Techeurope Hackathon #15*
- Custom object **`claims`** (`object_id c998a4db-29c8-411f-a6b4-ea8c944d846b`), 18 attributes:
  `correlation_id` (unique), `order_number`, `tracking_number`, `additional_tracking`,
  `delivery_postcode`, `phone_number`, `customer_comment`, `fraud_flags`,
  `courier` (select: Evri/DPD/Royal Mail/Yodel/Other), `claim_type` (select: Lost/Damage),
  `status` (pipeline: New → Pending → Raised → Accepted | Rejected | DOR | OnHold),
  `parcel_count`, `cost_value`, `parcel_value`, `settlement_amount`, `risk_score`,
  `customer` → people, `merchant` → companies (with inverse `claims` lists on both).
- **`companies.ceiling`** (number) added.
- Schema created by **`tools/attio_provision.py`** (idempotent). The Attio MCP is record-only — it cannot create objects/attributes, so schema is REST-only. See the memory note `attio-schema-via-rest`.
- **2 seeded claims** (status New): `clm-seed-0001` (Brand A, £20 ceiling, cost 35) and `clm-seed-0002` (Brand B, £25 ceiling, cost 18).

**Pricing rule modeled correctly:** `parcel_value` = merchant ceiling (the number submitted to Evri); `cost_value` = customer-stated cost; client credit = `min(cost_value, ceiling)`. Two distinct numbers — never conflated. See [[Evri File Formats]].

### n8n — `abdulmateen77.app.n8n.cloud`
- Workflow **`claims-loop`** (`id PQtAnonhUNBU8p7a`) — **Active**. Deployed via the n8n public REST API.
- **Production webhook:** `https://abdulmateen77.app.n8n.cloud/webhook/claim-intake`
- **Flow (Evri-only, Phase 1):**
  `Webhook (binary)` → `Generate correlation_id` (UUID + normalize + **server-side merchant resolve**) → **`Evri only?`** → if not Evri → `Respond: rejected (422)` *(no Attio writes)* ; if Evri → `Upsert Person` → `Upsert Merchant` → `Create Claim` → `Upload Photo` → `Process Claim (FastAPI)` → `Respond: processed (200)`.
- Attio **Header Auth** credential wired to the 4 Attio HTTP nodes.
- **Verified live:** non-Evri (DPD) → `422`, nothing created; Evri → person + merchant + claim + photo created in Attio, `status New`, `parcel_value 20` ≠ `cost_value`.

### Agent service — FastAPI
- New route **`POST /claims/{correlation_id}/process`** — Evri-gated; hydrates the claim from the request body *or* from Attio by `correlation_id`; runs **enrich → risk → decide → generate (byte-exact CSV) → mock dispatch**; **projects each status onto the Attio board** (New → Pending → Raised).
- **`app/agent/risk.py`** — deterministic fraud scoring (`risk_score` 0–100 + `fraud_flags`).
- **`app/integrations/attio.py`** — now reads (`get_claim_by_correlation_id`, resolves merchant name) and projects against the *real* schema.
- **9/9 tests pass** (byte-exact CSV snapshot intact). `/process` verified live: New → Pending → Raised + risk scoring on a throwaway claim.

---

## Current end-to-end flow
```
[Form] --multipart--> [n8n webhook /claim-intake]
        -> Generate correlation_id (idempotency key, server-side merchant)
        -> Evri only?  --no--> 422 reject (nothing written)
                       --yes-->
           Upsert Person -> Upsert Merchant -> Create Claim -> Upload Photo
           -> POST /claims/{id}/process  (FastAPI agent)
                  enrich -> risk -> decide -> generate CSV -> mock dispatch
                  -> projects New -> Pending -> Raised onto the Attio board
        -> 200 + claim reference
```
Attio is the live board the demo watches move. SQLite/in-memory is the agent's working store. See [[Architecture]] and [[State Machine & Data]].

---

## Pending
1. **Deploy the agent service publicly** with `ATTIO_API_KEY` set (Render via `render.yaml`, or a tunnel). Optional: `GEMINI_API_KEY`, `TAVILY_API_KEY`, `AFTERSHIP_API_KEY` — runs on deterministic stubs without them.
2. **Point the n8n `Process Claim` node** at the public agent URL (currently `localhost:8000`).
3. **AfterShip tracking verification** — replace the Tavily stub in the enrich step with real courier status. *(see plan below)*
4. **Verify Attio `/v2/files` field names** for the photo upload before relying on it.
5. *(Optional)* **Outcome loop** — 28-day Evri outcome → `/outcomes/ingest` → Accepted | Rejected | DOR (+ DOR resubmit). Endpoint exists; not yet driven by n8n.
6. **Point the live form** at the production webhook.
7. **Rotate** the Attio token + n8n API key (both were pasted in chat).

---

## AfterShip integration plan
**Goal:** confirm the tracking number genuinely shows non-delivery before a Lost claim is submitted to Evri — turning "customer says lost" into "carrier data agrees".

- **Where:** `app/agent/enrich.py` gains an AfterShip lookup: `(courier_slug, tracking_number) → { tag, last_checkpoint, delivered }`. Keep the stub fallback for offline demos.
- **How it feeds decisions:**
  - tag `Delivered` → **contradicts** a Lost claim → reject or high `risk_score` + flag.
  - tag `Exception` / `AttemptFail` / stalled `InTransit` / `InfoReceived` (label made, never scanned) → **supports** the Lost claim.
- **Stored on Attio:** the tracking summary + verdict can extend `fraud_flags` / `customer_comment`; the verdict gates `decide()`.
- **Needed to build it:** AfterShip **API key**, the **Evri courier slug** in the account (likely `evri` or `hermes`), and **1–2 sample tracking numbers** that exist in the account to test against.

---

## Rough time estimate
| Task | Estimate |
|---|---|
| Deploy agent + point n8n node | ~30 min (Render) / ~10 min (tunnel) |
| AfterShip integration (after data) | ~1–2 hrs |
| Verify `/v2/files` photo fields | ~30 min |
| Optional outcome loop | ~1–2 hrs |
| **Core live demo working** | **~30–45 min** |
| **Full (AfterShip + outcomes)** | **~half a day** |
