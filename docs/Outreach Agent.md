# Outreach Agent (Attio GTM)

How to find and reach SMBs with the Evri-claims problem, built as an agentic outbound loop in Attio. This is also the Attio track's flagship use case ("Outbound Email Agent" / "Research-to-CRM Pipeline").

## ICP - who actually bleeds
- UK **e-commerce / D2C** brands, **subscription-box** companies, small **3PLs / fulfilment houses**.
- Ship via **Evri** at meaningful volume.
- Too small for a claims team, big enough to feel the loss (~£5k-£50k/yr unclaimed).
- Often Shopify/Amazon; OMS like Mintsoft/ShipStation.

## Buying signals (target on evidence, not spray)
| Signal | Source |
|---|---|
| "Ships with Evri" | shipping/returns policy page, tracking links |
| Lost/damaged-parcel complaints | Trustpilot / Reviews.io |
| Ops/CS hiring for claims/couriers | LinkedIn / job boards |
| Volume indicators | SKU count, "ships X orders/day" |
| UK SMB filter | Companies House SIC codes |

The Trustpilot angle is strongest: a brand with many recent "Evri lost my parcel" reviews is visibly losing money + reputation.

## Attio data model
- **Company** object + custom attributes: `courier_used`, `est_monthly_parcels`, `evri_complaint_count`, `claims_pain_score`, `signal_source_url`.
- **Person** records: founder / ops lead + email.
- **List / pipeline**: `Sourced -> Enriched -> Scored -> Contacted -> Replied -> Booked`.

### Pain-score formula (example)
```
score = (evri_confirmed ? 40 : 0)
      + min(evri_complaint_count, 30)            # up to 30
      + (est_monthly_parcels > 2000 ? 30 : 15)
# route score >= 60 to outreach
```

## The autonomous loop (mirrors the product)
1. **Source** -> companies into Attio (CSV, Tavily web search, an Apify Trustpilot actor).
2. **Enrich** (Tavily + Gemini) -> confirm Evri usage, count complaints, find decision-maker + email.
3. **Score** -> set `claims_pain_score`; only high scores proceed.
4. **Draft** (Gemini) -> personalized email referencing the specific signal.
5. **Send / queue** -> fire via Attio or queue for one-click approval; log thread to the record.
6. **Follow up** -> Attio workflow handles 2-touch follow-up + status update.

## Message (money-first)
> Subject: you're probably owed £X from Evri
>
> Hi [name] - saw [N recent Trustpilot reviews] about Evri losing parcels. Every lost/damaged parcel is up to £25 you can claim back, but most brands never file because the process is fiddly and half get rejected on formatting. We built an agent that files them automatically - typically recovers £[X]/yr. Worth a 10-min look?

Angles, strongest first: recovered cash -> zero effort -> no format rejections. 4 sentences, one CTA, one named signal.

## Compliance (UK B2B)
Cold email to corporate/role addresses is allowed under legitimate interest (PECR/GDPR) with a clear opt-out. Target business not personal addresses; keep the pain-score as your documented legitimate-interest justification; don't scrape personal Gmail.

## Demo positioning
Two agents sharing a loop + a CRM:
- **Outbound agent** - finds Evri-bleeding SMBs, books them.
- **Claims agent** - serves them, recovers the money.

Default: demo the **claims agent** as the product, frame outbound as acquisition. To chase the Attio track hard, make the **outbound agent** the primary demo (cleaner fit for "close a deal with no human in the loop").

Related: [[Idea - Autonomous Claims Operator]] · [[Partner Tech]] · [[Technical Spec]]
