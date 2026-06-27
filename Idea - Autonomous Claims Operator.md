# Idea — Autonomous Claims Operator

## Pitch
Unrecovered courier claims are lost margin and a churn risk per client. Today a human formats fragile submission files by hand and a fraction get rejected on format errors alone. Our agent resolves each claim **case** autonomously — read, validate, decide, generate the exact file the courier accepts, dispatch, and follow the outcome through to settlement.

The hook: **the LLM is the brain, a deterministic generator is the hands.** AI decides; byte-exact code guarantees the file Evri accepts. Creativity (agentic) *and* technical depth (byte-exactness + state machine) in one story.

## The autonomous loop
1. **Ingest** — a claim arrives as free-text email / form (seeded for the demo).
2. **Extract** — Gemini turns messy text into a structured claim (order, tracking, loss/damage, value).
3. **Enrich** — Tavily validates postcode / looks up tracking status / courier policy.
4. **Decide** — eligibility rules (e.g. damage only on eligible channels; price at the ceiling).
5. **Generate** — byte-exact Evri submission CSV (the deterministic core).
6. **Dispatch** — (mocked) send; record the batch + state transition.
7. **Outcome** — replay a seeded outcome CSV → Accept / Reject / **DOR** evidence sub-flow.
8. **Write back** — status flows live into **Attio** as the case record updates.

## Why this idea
- Real, narrow, quantified pain (~20–30 claims/wk, ~£7k/yr lost to format rejections).
- The hard, impressive core (byte-exact generator + state machine) already exists to reuse.
- Maps cleanly onto an **agentic CRM** framing: a claim is a customer **case**; the agent acts on the data.

## Scope discipline
- **Must-demo path:** one **loss** claim, end to end, autonomously.
- **Nice-to-have:** damage flow, DOR evidence loop, multi-claim batch.
- **Out of scope today:** real OMS/Evri/email creds, the 28-day real outcome, multi-courier.

See [[Architecture]] for components and [[Build Plan & Timeline]] for the hour-by-hour.

Related: [[Feasibility]] · [[Hackathon Rules Compliance]] · [[Partner Tech]]
