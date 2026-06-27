# Partner Tech

Need **≥3**. We use **4 core + 2 bonus**.

## Core (each does real work in the loop)
| Tech | Role in our project | Setup |
|---|---|---|
| **Attio** | System of record + trigger surface + demo UI. Custom `Claim` object, status pipeline = our state machine, clients as Companies. Agent writes back via REST API / MCP. | Free workspace on the day. |
| **Gemini (DeepMind)** | The brain — extract structured claim from free text, classify loss/damage, decide eligibility, draft correspondence. | Temp accounts on site — goo.gle/hackathon-account. |
| **n8n** | Orchestrates the autonomous loop / triggers on new record. | Code: `2026-COMMUNITY-HACKATHON-LONDON-C089D711`. |
| **Tavily** | Enrichment — postcode validation, tracking status, courier-policy lookup (replaces live OMS). | Sign up → 1,000 free credits. |

## Bonus (cheap to add, side prizes)
| Tech | Role | Setup |
|---|---|---|
| **Aikido** | Security scan of the repo → screenshot for the side challenge (**€1000**). | Connect GitHub repo at 10:30. |
| **Minima / Mubit** | Route LLM calls to the cheapest model that clears the bar. | Key `mbt_…` from console.mubit.ai; redeem `MUBIT-LONDON-HACKATHON-JUNE`. |

## Not using (and why)
- **SLNG (voice)** — no natural voice surface in the must-demo path; revisit only if ahead of schedule.
- **Superlinked** — vector search over past outcomes is a great *stretch* (predict acceptance likelihood) but not core; add if time allows for the $500 side challenge.

Related: [[Architecture]] · [[Hackathon Rules Compliance]]
