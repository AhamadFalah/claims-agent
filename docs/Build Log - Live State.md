# Build Log — Live State

> What's actually stood up (Attio + n8n + agent service), what's verified, and what's still pending. Companion to [[Technical Spec]], [[Architecture]], [[Attio Schema Design]], [[Integrations Reference]].
> Snapshot: 2026-06-27.

## TL;DR
The Attio data model, the **live** n8n `outcome-replay` workflow (intake + Gemini validation + deterministic fusion + Firestore + outcome replay, all in one workflow, `id PQtAnonhUNBU8p7a`), and the FastAPI `/process` agent route are built and verified end-to-end — **including a full live run through the n8n hosted form**.

## Update — final live state (2026-06-27, later)
- **Intake is now an n8n hosted Form** (`Form: claim-intake`), not the raw webhook. Public form URL: `https://abdulmateen77.app.n8n.cloud/form/claim-intake`. The Code node maps the form's field labels and normalizes the uploaded photo to binary `data`.
- **AfterShip verification is built and live** (slug `myhermes-uk`, API `2026-01`). The agent gates on the carrier verdict: `Delivered` → Rejected, in-transit/out-for-delivery → **OnHold**, exception/no-scan → proceed. Verified live: a real `OutForDelivery` tracking drove a claim to **OnHold** with `risk_score 25`.
- **Single business**: merchant resolution + the `Upsert Merchant` node were removed. One fixed `const CEILING = 20` in the Code node sets `parcel_value`. Flow is now: `Form → Generate correlation_id → Evri only? → Upsert Person → Create Claim → Upload Photo → Process Claim → Respond` (9 nodes). Attio `merchant` attr + `companies.ceiling` remain in the schema, just unpopulated.
- **Agent reachability**: exposed to n8n Cloud via an **ephemeral cloudflared tunnel** (TryCloudflare). This URL changes on restart — **deploy to Render for a stable demo** and update the `Process Claim` node URL. The agent must run with `ATTIO_API_KEY` + `AFTERSHIP_API_KEY`.
- **Ceiling locked at £25** (`const CEILING = 25` in the n8n Code node).

## Update 2 — outcome loop live (2026-06-27, later still)
- **The loop now drives to outcome.** `/outcomes/ingest` resolves a claim Raised → **Accepted** (with settlement) / **Rejected** / **DOR**, and **hydrates the claim from Attio** when it's not in the agent's in-memory repo (`AttioClient.get_claim_by_tracking`) — so it survives agent restarts. Verified live: two `Raised` claims resolved via the tunnel → Accepted (`settlement 25`) and DOR, hydrated from Attio after an agent restart. Tests: `tests/test_outcomes.py` (in-memory + hydration), suite 12/12 green.
- **`n8n/outcome-replay.json`** — ops form ("Enter Evri Outcome": Tracking, outcome code, settlement) → `POST {AGENT}/outcomes/ingest` → Respond. **Deployed live** (id `Q58KdmBKv5UUrsae`, active) at `https://abdulmateen77.app.n8n.cloud/form/outcome-replay`. Verified live: resolved a Raised claim → Accepted (settlement 25).
- **`claims-loop` reset to the clean canonical flow** (10 nodes) after the canvas collision: removed the duplicate flow / re-added merchant / stray native AfterShip nodes; CEILING=25; added an `Attach photo` Code node that re-injects the form's binary (HTTP nodes drop it) so the photo actually uploads.
- ⚠️ **n8n canvas collision**: the live `claims-loop` was being hand-edited in the canvas (a full duplicate flow, a re-added `Upsert Merchant`, and native `AfterShip: Register Tracking` / `Get Status` nodes appeared). API-driven deploys and manual canvas edits fight each other. **Decide one owner for the workflow.**

## Update 3 — Gemini validation + Firestore merged into one workflow (2026-06-27, latest)
- **Everything is now a single n8n workflow named `outcome-replay`** (`id PQtAnonhUNBU8p7a`). The former `claims-loop` intake and the separate outcome-replay ops form were merged onto one canvas (the `Outcome: Evri result` form is a second trigger in the same workflow). The standalone `n8n/claims-loop.json` artifact was removed from the repo; **`n8n/outcome-replay.json` is now the canonical export**.
- **New validation stage (all LLM work done with the n8n AI Agent node):**
  `Upload Photo (optional) → Build VALIDATING doc → Firestore: write VALIDATING → Respond (early 200) → AI Agent: validate claim (Gemini multimodal + Structured Output Parser) → Fuse + decide → Attio: update status → Firestore: write VALIDATED → Process Claim (FastAPI)`, with the agent's error output → `Build ERROR doc → Firestore: write ERROR`.
- **Gemini is advisory only.** The agent returns a schema-locked verdict (`contract/verdict.schema.json`); the deterministic `Fuse + decide` node maps it to `AUTO_PROCEED → Raised`, `ESCALATE_HUMAN → OnHold`, failed gate → `AUTO_REJECT → Rejected`.
- **Firebase/Firestore** added: per-claim docs `VALIDATING → VALIDATED → ERROR` via the REST API. Needs `FIREBASE_PROJECT_ID` + a Firebase auth header credential (or `FIREBASE_API_KEY`).
- **Photo is optional** end-to-end: `Upload Photo` continues on a missing file (`onError`), the agent runs text-only when no image is attached, and the photo gate is no longer a hard reject in `Fuse + decide`.
- **Best-practice early response:** the form is acked right after the `VALIDATING` write, so the Gemini/fusion work runs asynchronously and a slow/failed LLM call never hangs the form.
- This repo was synced to match the live workflow (`n8n/outcome-replay.json`, `contract/verdict.schema.json`, `.env.example` Firebase vars). **No app code changed** — the FastAPI `/claims/{id}/process` and `/outcomes/ingest` contracts already match what n8n calls.
- **Mubit agent memory** added to the validation agent: two `HTTP Request Tool` sub-nodes (`Mubit: recall memory` → `POST /v2/control/query`, `Mubit: store memory` → `POST /v2/control/ingest`) connected via `ai_tool`. The agent recalls past lessons before deciding and stores one after. Auth via `MUBIT_API_KEY` (Bearer, env — not hardcoded). ⚠️ Verify the Mubit base URL and the query body field name against console.mubit.ai (the public docs don't pin them down).

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
