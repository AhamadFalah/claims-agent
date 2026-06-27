# Team & Roles

5 people. Each owns a vertical so we parallelize from 10:30.

| # | Role | Owns | Partner tech |
|---|---|---|---|
| 1 | **Agent lead** | Gemini prompts (extract + classify + decide); eligibility rules. | Gemini, Minima |
| 2 | **Orchestration lead** | n8n workflow; mock dispatch; seeded-outcome replay. | n8n |
| 3 | **Core lead** | Port generator + state machine + SQLite into the fresh repo; FastAPI; keep snapshot test green. | — |
| 4 | **Attio lead** | Workspace, `Claim` object + attributes, pipeline, API/MCP write-back. | Attio |
| 5 | **Glue / demo lead** | Tavily enrichment, seed data, Aikido setup, README + docs, Loom script, run-through. | Tavily, Aikido |

## Coordination rules
- **First 90 min:** Attio lead stands up the schema + seed records so everyone has a live target by lunch.
- **Connect Aikido at 10:30** so it scans all day.
- **Freeze at 17:30** — after that, demo recording + docs only.
- Must-demo path (one loss claim, end to end) is everyone's shared definition of done before stretch work.

Related: [[Build Plan & Timeline]] · [[Architecture]]
