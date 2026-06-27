# State Machine & Data

The contract for how a claim's `status` changes, plus the persistence schema. Pulled from the production repo (`state-machine.md`). All mutations go through `transition()`.

## Status enum
`New` -> `Pending` (validated/enriched) -> `Raised` (submitted) -> `Accepted` | `Rejected` | `DOR`. Plus `OnHold` (operator pause). `Accepted` and `Rejected` are **terminal**.

## Allowed transitions
```python
ALLOWED = {
    Status.NEW:     {Status.PENDING, Status.REJECTED, Status.ON_HOLD},
    Status.PENDING: {Status.RAISED, Status.REJECTED, Status.ON_HOLD},
    Status.RAISED:  {Status.ACCEPTED, Status.REJECTED, Status.DOR, Status.ON_HOLD},
    Status.DOR:     {Status.RAISED, Status.REJECTED, Status.ON_HOLD},
    Status.ON_HOLD: {Status.NEW, Status.PENDING, Status.RAISED, Status.DOR, Status.REJECTED},
    Status.ACCEPTED: set(),     # terminal
    Status.REJECTED: set(),     # terminal
}
```

## Transition narratives
- **NEW -> PENDING:** OMS enrichment ok; fields validated; T0/H0 routing applied.
- **NEW -> REJECTED:** auto-reject (e.g. damage on a non-eligible channel).
- **PENDING -> RAISED:** included in a dispatched batch; sets `submission_ref`.
- **RAISED -> ACCEPTED:** outcome `Accepted (DA1)`; sets `settlement_amount`.
- **RAISED -> REJECTED:** terminal rejection code.
- **RAISED -> DOR:** outcome SP1/SP3/SP4/P01.
- **DOR -> RAISED:** signed PDF received; CSV regenerated + sent to evidence address.
- **DOR -> REJECTED:** 7-day DOR timeout.
- **any -> ON_HOLD:** manual pause.

### Terminal rule
Once `Accepted`/`Rejected`, never moves again. An outcome arriving for a terminal claim is **logged and ignored**, not overwritten.

## DOR sub-workflow
Runs while main status is `DOR`:
```python
DorState: AwaitingClient -> Reminded(day 3) -> Received -> Resubmitted
                         \-> Timeout(day 7)  -> main status REJECTED
```
Day 0: generate DOR letter (DOCX), email client, `AwaitingClient`. Day 3: reminder. Day 7: timeout -> `Rejected (DOR Timeout)`. On signed PDF (<=7d): store, regenerate CSV with `DOR LETTER DATE`, resend to evidence address, main status -> `Raised`.

## `transition()` rules
- Single point where status changes; workflows never assign `claim.status` directly.
- Audit log entry written **in the same DB transaction** - if audit fails, the status update rolls back.
- Idempotent: repeating the same transition is a no-op (from-status no longer matches).

## Persistence schema (SQLite / SQLAlchemy 2.x)
- **claims** - one row per claim; current `status`, `correlation_id` (unique), `channel_id`, `courier`, `claim_type`, `tracking_number`, `barcode_prefix`, `order_number`, `postcode`, `cost_value`, `parcel_value`, `status_reason`, `submission_ref`, `settlement_amount`, `investigation_required`, timestamps.
- **batches** - one per generated file; `provider`, `file_path`, `file_sha256`, provider ids (ticket/thread/message), `sent_at`, `sent_by`.
- **batch_items** - M:N claims<->batches; `row_position` (1-indexed, matches CSV row for error mapping).
- **outcomes** - one per verdict event; raw `code`, raw `claim_status`, `settlement_amount`, `inbound_ref`, `raw_row` (JSON), `received_at`.
- **dor_workflow** - one per DOR instance; `dor_state` + timestamps + `pdf_path`.
- **audit_log** - immutable; `correlation_id`, `actor`, `action`, `entity_type/id`, `before`/`after` (JSON), `reason`, `timestamp`.
- **sheet_cursor** - `last_row` per sheet for incremental ingest.

## Hackathon simplification
For the MVP, SQLite is the source of truth and Attio is the live projection. You can drop `batch_items`, `dor_workflow` detail, and `sheet_cursor` if time is tight - keep `claims`, `outcomes`, and `audit_log`.

Related: [[Technical Spec]] · [[Evri File Formats]] · [[Integrations Reference]]
