# Integrations Reference

Full integration detail from the production repo (`integrations.md`), vendor names generalized. Each integration = one module, a `Client` class, typed exceptions, `tenacity` retries, no direct env reads (config injected).

## OMS (canonical order data)
Canonical source for customer name, postcode, order value, despatch date. **OMS wins** on conflict with the spreadsheet.
- Token auth: `POST /api/Auth {username, password}` -> token in `ms-apikey` header. **Tokens expire 24h** - cache in memory, refresh on `401`.
- Credentials: `OMS_USERNAME` / `OMS_PASSWORD` (NOT an API key - the token is derived from the password).
- **No get-by-order-number endpoint.** Use `GET /api/Order/Search?OrderNumber=...&exactMatch=true`, then `GET /api/Order/{id}`. Also `/api/Order/{id}/Shipments`, `/api/Order/Statuses`.
- Typed failures: `AuthError` (401), `RateLimited` (429), `OrderNotFound` (0 results), `ServerError` (5xx).
- Retry: auth -> refresh once + retry; 429/5xx -> exp backoff w/ jitter, max 3; not-found -> no retry, return `None`.
- **Hackathon:** replace with seeded fixtures + Tavily. Do not wire live.

## Spreadsheet tracker (19-column contract)
Form fills cols 1-15; system writes **16 (Status), 17 (Comment), 19 (Credit Date)**; **never 18 (Amount)** - operator-only.
- Read cols incl. Client (3), Mintsoft/OMS Order Number (5), Courier (6, filter == `Evri`), Loss/Damage (7), Tracking (9), Postcode (11), Cost Value (14).
- Status enum (col 16): blank, `Raised`, `Accepted`, `Rejected`, `DOR`, `OnHold`.
- Comment (col 17) write rules: blank->Raised = submission ref; Raised->Accepted = append ` - credit £X`; Raised->Rejected = `code - reason`; ->OnHold = free text.
- Auth: service-account JSON; sheet shared as Editor (fail fast if Viewer).
- **Batch updates only** - single-cell writes hit the ~60 writes/min rate limit.
- Incremental reads via `sheet_cursor` (process rows > last_row; advance in same tx).
- **Hackathon:** Attio replaces this surface entirely.

## Ticketing channel (non-premium clients)
Email-via-helpdesk. OAuth2 client + refresh token; EU region base `https://desk.zoho.eu/api/v1`; needs a department id.
- Send: `POST /tickets` with contact = Evri submissions address, channel Email, attachments. Response `id` = the ticket id stored on the batch.
- Outbound subject exactly `Evri Claim DD/MM/YY` (helpdesk adds the `[## id ##]` tag on replies - do not set manually).
- Replies: same ticket for the immediate ref; later replies = new ticket tagged `[## id ##]`.

## Direct-mailbox channel (premium clients)
Workspace service account with **domain-wide delegation**, impersonating the channel mailbox via `subject=<mailbox>`.
- Scopes: `spreadsheets`, `drive.file`, `gmail.send`, `gmail.readonly`.
- Send: build MIME, `users().messages().send`. Capture `message id` + `thread id` on the batch.
- Receive: poll mailbox, match by thread id or the 6-6 submission ref regex.
- **Go-live blocker:** domain-wide delegation for `gmail.send` must be enabled in the Workspace admin console.

## Document store
Signed DOR PDFs (and Phase-2 photo evidence). Store stable file id on `dor_workflow.pdf_path` (URLs change, ids don't).

## SMTP fallback
Emergency only; disabled by default; per-send CLI approval. Not a routine path.

## Hackathon partner integrations (new)
- **Attio** REST v2 - `claim` object + status pipeline; upsert by `correlation_id`. See [[Technical Spec]].
- **Gemini** - structured extraction (`response_schema`).
- **Tavily** - enrichment search.
- **Minima/Mubit** - LLM model routing.
- **n8n** - orchestration.
See [[Partner Tech]] for keys/codes.

Related: [[Technical Spec]] · [[State Machine & Data]] · [[Evri File Formats]]
