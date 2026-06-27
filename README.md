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
n8n/            claims-loop.json — the orchestration workflow
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
`Read` (Gemini) → `Enrich` (Tavily) → `Decide` (rules) → `Generate` (byte-exact CSV)
→ `Dispatch` (mock) → `Resolve` (state machine + outcome). Status writes back to
Attio live. See [docs/Technical Spec](docs/Technical%20Spec.md).

## Run the loop end-to-end (offline)
```bash
# 1. start the service:  uvicorn app.main:app
# 2. POST a seeded claim, then walk the steps:
curl -s localhost:8000/claims/extract -H 'content-type: application/json' \
     -d @data/samples/claim_email.json
# then /claims/{id}/enrich, /claims/{id}/decide, /batches/dispatch,
# and /outcomes/ingest with a row from data/samples/outcomes.json
```
Or import `n8n/claims-loop.json` into n8n and POST to its `claim-intake` webhook.

## Partner technologies — what each does, and where in the code
| Technology | Role in the project | Where |
|---|---|---|
| **Attio** | System of record + live case board; each claim is a record, status attribute = the pipeline. Upsert by `correlation_id`. | [`app/integrations/attio.py`](app/integrations/attio.py) |
| **Google Gemini** | Reads the free-text claim email and returns a structured, schema-validated claim (judgment, not formatting). | [`app/agent/extract.py`](app/agent/extract.py) |
| **n8n** | Orchestrates the autonomous loop — webhook trigger chains the agent endpoints. | [`n8n/claims-loop.json`](n8n/claims-loop.json) |
| **Tavily** | Enriches the claim (tracking status / address sanity). | [`app/agent/enrich.py`](app/agent/enrich.py) |
| **Aikido** | Security scanning of this repo (CI/code scan). | repo-connected |
| **Minima / Mubit** | Routes each LLM call to the cheapest model that clears the quality bar. | [`app/agent/route.py`](app/agent/route.py) |

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
