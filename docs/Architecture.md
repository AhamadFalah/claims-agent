# Architecture

## Flow
```
claim email/form (seeded)
        │
        ▼
  [n8n trigger] ──► Agent service (FastAPI)
        │                 │
        │        ┌────────┼─────────────┐
        │        ▼        ▼             ▼
        │     Gemini    Tavily     Eligibility
        │   (extract)  (enrich)     (decide)
        │                 │
        │                 ▼
        │        Byte-exact CSV generator  ──► (mock dispatch)
        │                 │
        │                 ▼
        │          State machine + SQLite
        │                 │
        └────────────────►└──► write back to ATTIO (case status updates live)
                                       ▲
                       seeded outcome CSV replay (Accept/Reject/DOR)
```

## Components
| Component                      | Build vs reuse          | Notes                                                              |
| ------------------------------ | ----------------------- | ------------------------------------------------------------------ |
| Agent service (FastAPI)        | New                     | Exposes the loop steps; called by n8n.                             |
| Gemini extraction + decision   | New                     | Prompts for extract + classify + eligibility.                      |
| Tavily enrichment              | New                     | Postcode/tracking/policy lookups.                                  |
| Byte-exact Evri CSV generator  | **Adapted utility** | 13-col, CRLF, no BOM, exact header; snapshot test must stay green. |
| State machine + transitions    | **Adapted utility** | New→Pending→Raised→Accepted/Rejected/DOR (+OnHold).                |
| Persistence                    | New/port                | SQLite; or lean on Attio as record store.                          |
| Attio integration              | New                     | REST API / MCP write-back; custom `Claim` object + pipeline.       |
| Mock dispatch + outcome replay | New                     | Buttons/fixtures to simulate Evri round-trip.                      |
| Minima routing                 | New                     | Wraps LLM calls.                                                   |

## Demo scope
The agent loop, Gemini decisions, Tavily lookups, byte-exact generation, state transitions, and live Attio updates all run for real. Integrations are credential-gated: with API keys set they call the live services, and without keys they fall back to deterministic stubs so the demo runs offline. Evri itself has no submission API (it is email-driven), so dispatch is a mock and the 28-day outcome is replayed from a seeded fixture.

## Stack
Python 3.11+, FastAPI (agent service), reuse of the existing generator/state-machine; Attio + n8n + Gemini + Tavily as integrations. Keep dependency surface small.

Related: [[Idea - Autonomous Claims Operator]] · [[Partner Tech]] · [[Build Plan & Timeline]]
