# 00 Home — Tech:Europe London AI Hackathon

Map of content for our hackathon entry. One-day event, submit by **19:00**, demos **20:00**.

## Strategy & planning
- **Idea:** [[Idea - Autonomous Claims Operator]]
- **Is it doable today?** [[Feasibility]]
- **Are we allowed to submit it?** [[Hackathon Rules Compliance]]
- **How we build it:** [[Build Plan & Timeline]]
- **Who builds what:** [[Team & Roles]]
- **Required tools:** [[Partner Tech]]
- **What we say:** [[Pitch]]

## Technical reference
- **Build-level spec (code, API, services):** [[Technical Spec]]
- **System flow + components:** [[Architecture]]
- **Byte-exact CSV rules:** [[Evri File Formats]]
- **Status transitions + DB schema:** [[State Machine & Data]]
- **OMS / spreadsheet / channels / partner APIs:** [[Integrations Reference]]

## Go-to-market
- **Attio outbound playbook:** [[Outreach Agent]]

## The one-liner
> An **autonomous courier-claims operator**: a claim email lands, an AI agent reads it, validates it, decides eligibility, generates a byte-exact Evri submission, and drives it to outcome — no human in the loop.

## Key facts
- Team of **5**. Track: **Open Innovation** (build natively on **Attio** to also chase the Attio track).
- Demo-path MVP on **seeded data** — nothing wired to live courier/OMS/email creds.
- Must use **≥3 partner technologies** → we use 4 core + 2 bonus. See [[Partner Tech]].
- Built **new today**; reuse the byte-exact CSV generator + state machine as clearly-attributed boilerplate.
