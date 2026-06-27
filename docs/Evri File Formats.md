# Evri File Formats

Byte-exact requirements pulled from the production repo (`format-rules.md`). Violating any of these causes Evri to reject the submission. The golden reference is `tests/fixtures/evri_apr07_real.csv` (**656 bytes, 4 lines**, 1 header + 3 rows, CRLF-terminated).

## Submission CSV - encoding
| Property | Required value | Why |
|---|---|---|
| Encoding | UTF-8 **without BOM** | Evri's parser misreads a BOM as part of column 1. |
| Line endings | CRLF (`\r\n`) | Required by Evri ingestion. |
| Final newline | Yes - last line also ends `\r\n` | Reference file has it; tests assert it. |
| Write mode | **binary (`wb`)** | Text mode on Windows turns `\n` into `\r\r\n`. |

Correct:
```python
content = header + "\r\n" + "\r\n".join(rows) + "\r\n"
open(path, "wb").write(content.encode("utf-8"))
```
Wrong: text mode (mangles endings), `utf-8-sig` (adds BOM), `"\n".join` (LF not CRLF).

## Submission CSV - 13 columns (exact order + names)
| # | Header | Notes |
|---|---|---|
| 1 | `␣CLIENT REFERNCE NO` | **Leading space.** `REFERNCE` is a deliberate misspelling. **18 chars.** |
| 2 | `BRAND NAME` | Channel display name. |
| 3 | `HERMES BARCODE` | `T0...` or `H0...` prefix (= routing). |
| 4 | `ORDER NO` | OMS order number incl. any prefix. |
| 5 | `CUSTOMER NAME` | Always the literal `Customer`. Never the real name. |
| 6 | `POSTCODE` | UK postcode with a space (e.g. `SW6 2TZ`). |
| 7 | `DOR LETTER DATE` | Empty on first submission; populated on DOR resubmit (`dd/mm/yyyy`). |
| 8 | `CLIENT OR CUSTOMER COMMENTS` | Per-claim; defaults differ by claim type. |
| 9 | `PARCEL VALUE` | The channel **ceiling as integer** (`20` or `25`), not the cost value. |
| 10 | `PRODUCT CATEGORY` | Always the literal `Other`. |
| 11 | `PRODUCT DESCRIPTION` | `Loss` for loss; per-channel override for damage. |
| 12 | `CARRIAGE` | Always empty. |
| 13 | `LOST OR DAMAGED` | `Lost Claim` or `Damage Claim` (note trailing "Claim"). |

## The single most fragile detail
Column 1 header is exactly: a space, `CLIENT`, space, `REFERNCE` (R-E-F-E-R-N-C-E), space, `NO`. First 20 bytes in hex:
```
20 43 4c 49 45 4e 54 20 52 45 46 45 52 4e 43 45 20 4e 4f 2c
```
(`␣CLIENT REFERNCE NO,`). Never "fix" the typo - the parser keys off this string.

## Per-claim defaults
- Col 8 (comments), loss: `Consignment lost or Tracking not update`
- Col 8 (comments), damage: `Item arrived damaged`
- Col 11 (description), loss: `Loss`
- Col 11 (description), damage: channel-specific override.

## Forbidden in fields
- **No commas** in col 8 (comments) or col 6 (postcode) - strip/replace at source.
- **No double-quotes** anywhere. **No newlines** within a field.
- Fields are **never quoted**. A value containing a comma is a bug (unsanitised input).

## Row ordering
By **channel**, then **claim insertion time** within channel. Never alphabetical, never by tracking number.

## Outcome CSV (inbound, 28 days later)
- **24 columns** (Evri appends internal columns). UTF-8 no BOM; LF or CRLF both seen - `csv.reader` handles either.
- **Match key:** `HERMES BARCODE`.
- **Status column:** `Claim Status` - stored verbatim, never remapped.
- Email body carries `File reference NNNNNN-NNNNNN` - capture + store.

### Outcome code -> action
| Evri code | Action | Reason |
|---|---|---|
| `Accepted (DA1)` | -> `Accepted`, record settlement | Standard accept |
| `Rejected (OOT)` | -> `Rejected` | Out of time (past 28-day window) |
| `Rejected (DUP)` | -> `Rejected` | Duplicate; flag for ops |
| `Rejected (DA2)` | -> `Rejected` | Damage not eligible |
| `SP1`,`SP3`,`SP4`,`P01` | -> `DOR` (trigger sub-workflow) | Customer must sign Declaration of Receipt |
| `NC1`,`NT2` | -> `Rejected` + `investigation_required` | Anomalous |
| `LIN1`,`LIN4` | -> `Rejected` | Tracking-link issues |
| `Damage claim not covered` | -> `Rejected` (terminal) | Channel ineligible for damage |
Runtime source: `config/data/outcomes.yaml`.

## Submission reply matching
1. **Submission reference** (<2 min): body has `260428-014769` (regex `\b(\d{6}-\d{6})\b`).
2. **Submission errors** (<30 min): "Unregistered Merchant" (15 cols) or "Duplicate row" (2 cols).
- Ticketing channel: reply lands in the same ticket; later replies arrive as a new ticket tagged `[## NNNNNN ##]` (regex `\[##\s*(\d+)\s*##\]`).
- Direct-mailbox channel: reply in same thread; match thread id or the 6-6 ref.

## DOR resubmission CSV
Same 13-col format, except: col 7 `DOR LETTER DATE` populated (`dd/mm/yyyy`); send to Evri's evidence address; signed PDF attached.

Related: [[Technical Spec]] · [[State Machine & Data]]
