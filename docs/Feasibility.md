# Feasibility

**Verdict: feasible as a demo-path MVP. Not feasible as the real production system.**

The dominant constraint is time: a **one-day** event with a **~6–7 hour** build window (matchmaking 10:00, lunch 12:30, submit 19:00). We start ahead because the domain logic, state machine, and a working byte-exact CSV engine already exist to reuse as boilerplate.

## What makes it feasible
- The hard, impressive core (byte-exact generator + snapshot test) is **self-contained and offline** — no external services on the critical path.
- The domain model + state machine + SQLite are already designed; we port, not invent.
- Using **Attio** as system-of-record + UI removes the dashboard *and* DB build work.
- A narrow, quantified problem is easy to pitch in 2 minutes.

## What is NOT feasible today (so we fake it)
| Risky / slow | Demo approach |
|---|---|
| Live OMS login | Seeded order data |
| Google domain-wide delegation / `gmail.send` | Mock dispatch |
| Ticketing OAuth, real Evri mailboxes | Mock dispatch |
| Real 28-day Evri outcome | Replay a seeded outcome CSV on a button |
| Live courier/tracking APIs | Tavily lookups + seeded fixtures |

## Top risks
1. **Scope creep** — lock the must-demo path (one loss claim, end to end) before touching DOR/damage.
2. **New-tool learning curve** — Attio + n8n under a 7h clock; mitigate by setting up Attio schema in the first 90 min.
3. **Integration glue** — if n8n fights us, a Python scheduler runs the loop and n8n triggers/visualizes one stage (still satisfies the requirement).
4. **"Newly created" optics** — attribute boilerplate clearly; build the agentic layer fresh today.

## Confidence
- One loss claim, autonomous, end to end, with live Attio updates: **high**.
- Full DOR + damage + multi-claim polish: **medium** (treat as stretch).

Related: [[Idea - Autonomous Claims Operator]] · [[Hackathon Rules Compliance]] · [[Build Plan & Timeline]]
