# Autonomous Claims Operator

> An AI agent that reads a courier-claim email, validates it, decides eligibility,
> generates the **byte-exact** Evri submission file, and drives it to outcome — with
> no human in the loop. Built for the Tech:Europe London AI Hackathon.

The LLM is the brain (judgment); a deterministic generator is the hands (the file
Evri's parser accepts, correct to the byte).

## Monorepo layout
```
app/            FastAPI agent service — the loop, one endpoint per step
  domain/       Claim model + state machine (the only place status changes)
  agent/        extract (Gemini) · enrich (Tavily) · decide · route (Minima)
  generators/   byte-exact Evri CSV generator
  integrations/ Attio (live board) · mock dispatch
  persistence/  in-memory repo (swap for SQLite)
  config/       channels.yaml · outcomes.yaml
tests/          snapshot test (byte-equality) + state-machine tests
tools/          build_fixture.py — regenerate the golden CSV
n8n/            outcome-replay.json — the deployed orchestration workflow
contract/       verdict.schema.json — the Gemini validation verdict contract
data/samples/   seeded claim email + outcomes for the demo
docs/           the team knowledge base (open as an Obsidian vault)
```

## Quick start
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"          # add ".[dev,agents]" to enable live Gemini/Tavily/Minima
cp .env.example .env             # optional — runs with offline stubs if empty

pytest -q                        # 9 tests, incl. the byte-exact snapshot
uvicorn app.main:app --reload    # agent service on :8000
```

Everything runs **without any API keys** — each integration falls back to a stub,
so the demo works offline. Add keys in `.env` to go live with each partner tool.

## The loop
The deployed loop runs in n8n (`n8n/outcome-replay.json`) and calls this FastAPI
service for the deterministic "hands" steps:

`Form intake` → `Evri-only gate` → `Attio upsert Person + create Claim` →
`Upload Photo` (optional) → `Firestore: VALIDATING` → **early 200 to the form** →
`AI Agent: validate claim` (Gemini, multimodal, schema-locked verdict) →
`Fuse + decide` (deterministic gates + confidence → AUTO_PROCEED / ESCALATE_HUMAN /
AUTO_REJECT) → `Attio: update status` (Raised / OnHold / Rejected) →
`Firestore: VALIDATED` → `POST /claims/{id}/process` (this service: byte-exact Evri
CSV → mock dispatch). A separate **Outcome** form replays the 28-day Evri result via
`POST /outcomes/ingest`, driving Raised → Accepted/Rejected/DOR.

The Gemini agent is **advisory only** — the deterministic `Fuse + decide` node owns
the real decision, and the verdict is locked to [`contract/verdict.schema.json`](contract/verdict.schema.json).
See [docs/Technical Spec](docs/Technical%20Spec.md).

## Run the loop end-to-end (offline)
```bash
# 1. start the service:  uvicorn app.main:app
# 2. POST a seeded claim, then walk the steps:
curl -s localhost:8000/claims/extract -H 'content-type: application/json' \
     -d @data/samples/claim_email.json
# then /claims/{id}/enrich, /claims/{id}/decide, /batches/dispatch,
# and /outcomes/ingest with a row from data/samples/outcomes.json
```
Or import `n8n/outcome-replay.json` into n8n and submit the **`claim-intake`** form
(it drives the full pipeline above). Set `AGENT_BASE_URL` in n8n to this service's URL.

## Partner technologies — what each does, and where in the code
| Technology | Role in the project | Where |
|---|---|---|
| **Attio** | System of record + live case board; each claim is a record, status attribute = the pipeline. Upsert by `correlation_id`. | [`app/integrations/attio.py`](app/integrations/attio.py) |
| **Google Gemini** | In n8n: a multimodal **AI Agent** cross-checks the claim + photo and returns a schema-locked verdict ([`contract/verdict.schema.json`](contract/verdict.schema.json)). In the app: structured claim extraction. | `n8n/outcome-replay.json` · [`app/agent/extract.py`](app/agent/extract.py) |
| **n8n** | Orchestrates the autonomous loop — Form trigger → Attio → Firestore → Gemini validation → deterministic fusion → FastAPI process. | [`n8n/outcome-replay.json`](n8n/outcome-replay.json) |
| **Firebase / Firestore** | Per-claim validation document store; states `VALIDATING → VALIDATED → ERROR` written via the REST API as the claim moves through validation. | `n8n/outcome-replay.json` (Firestore nodes) |
| **Tavily** | Enriches the claim (tracking status / address sanity). | [`app/agent/enrich.py`](app/agent/enrich.py) |
| **Aikido** | Security scanning of this repo (CI/code scan). | repo-connected |
| **Minima / Mubit** | (1) Routes each LLM call to the cheapest model that clears the quality bar. (2) **Agent memory** for the n8n validation agent — two HTTP Request tools call Mubit control-http (`/v2/control/query` to recall, `/v2/control/ingest` to store) so the agent learns from past claims. | [`app/agent/route.py`](app/agent/route.py) · `n8n/outcome-replay.json` |

Each integration calls the live service when its API key is set and otherwise
falls back to a deterministic stub, so the project is runnable and testable with
zero credentials. More detail in [docs/Partner Tech](docs/Partner%20Tech.md).

## Docs / team knowledge base
Open the `docs/` folder as an Obsidian vault, or browse on GitHub starting at
[docs/00 Home](docs/00%20Home.md). Reference: [Evri File Formats](docs/Evri%20File%20Formats.md),
[State Machine & Data](docs/State%20Machine%20%26%20Data.md),
[Integrations Reference](docs/Integrations%20Reference.md),
[Pitch](docs/Pitch.md), [Build Plan & Timeline](docs/Build%20Plan%20%26%20Timeline.md).

## What was built at the hackathon
Built new for this event: the agentic loop, every partner-tool integration
(Attio, Gemini, Tavily, n8n, Minima), the FastAPI service, the orchestration
workflow, the test suite, and the demo. As permitted by the rules, two small,
self-contained deterministic utilities — the Evri CSV byte-formatter and the
claim state-machine — are adapted from prior work and noted here for transparency;
they are the "hands," and everything that makes this an autonomous agent is new.

## License
MIT — see [LICENSE](LICENSE).
