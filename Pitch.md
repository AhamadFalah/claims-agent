# Pitch

## Teammate rally (~60s)
> Every 3PL loses real money on courier claims - not because the claims are invalid, but because a human formats a fragile file by hand and the courier's parser rejects it on a misplaced comma. Thousands a year, gone to typos.
>
> We're building an autonomous claims operator. A claim lands, an AI agent reads the messy email, validates it, decides eligibility, and generates the byte-exact file the courier accepts - then drives it to settlement. No human in the loop.
>
> Why it wins: most teams demo a chatbot. We demo an agent that takes a real action with a guaranteed-correct output. The LLM is the brain, our deterministic generator is the hands - creativity and hard engineering in one story.
>
> We're not starting from zero - we have a working byte-exact generator and state machine to reuse as boilerplate. So in 7 hours we build the agent layer, wire 4 partner tools, ship a clean demo on seeded data.
>
> Five of us, five lanes: Gemini brain, n8n loop, Attio live board, the core engine, glue + demo. Lock the one-claim path first; everything else is stretch. Let's go.

## Judge - 2-minute (Loom + pre-selection)
- **0:00-0:20 Problem:** 3PLs lose thousands/yr on claims they're entitled to - rejected on formatting, not merit. Lost margin + churn risk.
- **0:20-0:40 Idea:** "We built an autonomous claims operator. A claim email arrives - no one touches it."
- **0:40-1:20 Live demo:** Gemini extracts the structured claim -> Tavily enriches (address/tracking) -> eligibility decision -> **byte-exact** submission file (exact columns, CRLF, the header typo the parser needs) -> snapshot test proves byte-correctness -> n8n runs the loop -> watch the case move New -> Raised -> Accepted live in Attio.
- **1:20-1:45 Why different:** most agents suggest; ours acts, and the output is guaranteed-correct - LLM for judgment, determinism for the part that can't be wrong.
- **1:45-2:00 Close:** a whole back-office workflow run end to end, no human in the loop - on Attio, Gemini, n8n, Tavily.

## Judge - 5-minute (finalist) - extra beats
1. Open with the number (~£7k/yr at one small firm; multiply across the industry).
2. Spine demo (2 min) - slow down on the live Attio board updating itself.
3. The hard part, shown (1 min) - snapshot test on screen; explain the header typo. Technical-complexity moment.
4. Outcome loop (45s) - replay Accept and the DOR evidence sub-flow auto-starting.
5. Architecture + partner tech (30s) - one slide; 4 techs each doing real work + Aikido scanning the repo.
6. Close on the pattern (15s) - same shape fits insurance, regulatory filings, EDI. We built the template.

## Delivery tips
- Lead with live action, narrate less - let the Attio board move on its own.
- Say "no human in the loop" out loud (the track's literal north star).
- Name-drop partner tech in the flow, not a list.
- Own the byte-exact typo detail - memorable + proves real-world understanding.

Related: [[Idea - Autonomous Claims Operator]] · [[Hackathon Rules Compliance]] · [[Outreach Agent]]
