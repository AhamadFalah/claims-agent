# Build Plan & Timeline

One-day event. **Hard freeze 17:30. Submit by 19:00.**

## Hour-by-hour
| Time | Focus |
|---|---|
| 09:30–10:00 | Doors / networking. |
| 10:00–10:30 | Opening + matchmaking; confirm roles ([[Team & Roles]]); grab submission form URL from Discord. |
| 10:30–11:00 | **Setup.** Fresh **public** repo. Accounts: Gemini, Tavily, n8n code, Mubit key + redeem. **Connect repo to Aikido now.** |
| 11:00–13:00 | **Parallel build.** Core API + green snapshot / Gemini extraction / n8n skeleton / Attio schema + seed / seed data. Stagger lunch ~12:30. |
| 13:00–15:30 | **Wire the spine** on one seeded loss claim: email → Gemini → Tavily → generate CSV → state transition → Attio updates live. |
| 15:30–17:00 | **Polish.** Outcome-replay button (Accept/Reject/DOR), Minima in, demo flow rehearsal. |
| 17:00–17:30 | **Freeze.** Last critical bug only. |
| 17:30–18:30 | Record 2-min Loom; README + docs; Aikido screenshot. |
| 18:30–19:00 | **Submit** (buffer for form gremlins). |
| 20:00 | Live demos. |

## Definition of done (MVP)
- One **loss** claim runs end-to-end **autonomously** and its case status updates live in Attio.
- Snapshot test for the byte-exact CSV is green.
- ≥3 partner techs visibly doing real work.
- Loom recorded, repo public with README, Aikido screenshot captured.

## Stretch (only after MVP is solid)
- DOR evidence sub-flow; damage-claim path; multi-claim batch; Superlinked acceptance-likelihood; SLNG voice query.

## Fallbacks
- n8n misbehaves → Python scheduler runs the loop, n8n triggers one stage.
- Attio Workflows fight back → Attio as record store + UI only, loop driven externally.

Related: [[Feasibility]] · [[Architecture]] · [[Hackathon Rules Compliance]] · [[Team & Roles]]
