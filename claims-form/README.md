# claims-form

Customer-facing parcel claims intake form (React + Vite + TypeScript).

This is a **standalone public web app** — it is *not* an Attio App SDK component. It collects a claim from the customer and POSTs it as `multipart/form-data` to an **n8n webhook**, which holds the Attio token and creates the records in Attio (Person → Claim → File). See `../Attio Schema Design.md` for the full pipeline and the operator side.

```
React form (this app)  ──multipart──▶  n8n webhook  ──Attio token──▶  Attio REST API
```

> ⚠️ The Attio API token must **never** live in this app. Anything prefixed `VITE_` is bundled into the browser and visible to every visitor. The form only ever knows the n8n URL.

## Setup

```bash
cd claims-form
npm install
cp .env.example .env        # then set VITE_N8N_WEBHOOK_URL to your n8n webhook
npm run dev                 # http://localhost:5173
```

## Scripts

| Command | What it does |
|---|---|
| `npm run dev` | Start the Vite dev server. |
| `npm run build` | Type-check and build to `dist/`. |
| `npm run preview` | Serve the production build locally. |
| `npm run typecheck` | Type-check only. |

## Form fields → multipart field names

These match the Attio `claims` attribute slugs so the n8n nodes can map them directly:

| Field name (sent) | Attio target |
|---|---|
| `name`, `email`, `phone_number` | `people` record (upsert by email) |
| `order_number`, `courier`, `claim_type`, `parcel_count` | `claims` |
| `tracking_number`, `additional_tracking`, `delivery_postcode` | `claims` |
| `customer_comment`, `parcel_value` | `claims` |
| `photo` (binary) | `POST /v2/files`, linked to the new claim |

The **merchant** is *not* collected here — n8n derives it server-side (see schema doc).

## Note on file structure

`src/`
- `App.tsx` — page shell
- `ClaimForm.tsx` — the form + submit states
- `validation.ts` — client-side validation
- `submitClaim.ts` — builds FormData, POSTs to the n8n webhook
- `types.ts` — field option lists + form value shapes
