#!/usr/bin/env python3
"""Provision the Attio data model for the claims agent.

The Attio **MCP** server is data-plane only (it creates records, not schema), so
the custom object + attributes have to be created through the Attio **REST API**,
which needs an API key. This script does exactly that, idempotently:

  * creates the `claims` custom object
  * creates every `claims` attribute (with select options + status pipeline)
  * adds the `ceiling` number attribute to the standard `companies` object

Re-running is safe: anything that already exists returns HTTP 409 and is skipped,
so the script converges to the target schema.

Usage:
    export ATTIO_API_KEY=...        # token with scope: object_configuration:read-write
    python3 tools/attio_provision.py            # create everything
    python3 tools/attio_provision.py --verify   # just print object + attribute ids

cost_value vs parcel_value are deliberately TWO separate number attributes:
  - cost_value     = customer-stated cost of goods
  - parcel_value   = the merchant ceiling actually submitted to Evri
  - client credit  = min(cost_value, ceiling)   (computed downstream, not stored here)
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

BASE = "https://api.attio.com/v2"
CLAIM_OBJECT = "claims"


def _load_dotenv() -> None:
    """Minimal .env loader so ATTIO_API_KEY can live in .env (never committed)."""
    path = os.path.join(os.path.dirname(__file__), os.pardir, ".env")
    if not os.path.exists(path):
        return
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())


_load_dotenv()
TOKEN = os.getenv("ATTIO_API_KEY")


def req(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(f"{BASE}{path}", data=data, method=method)
    request.add_header("Authorization", f"Bearer {TOKEN}")
    request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request) as resp:
            return resp.status, json.loads(resp.read() or "{}")
    except urllib.error.HTTPError as exc:
        try:
            payload = json.loads(exc.read() or "{}")
        except Exception:
            payload = {}
        return exc.code, payload


def _ok(status: int) -> bool:
    return 200 <= status < 300


def die(what: str, status: int, body: dict) -> None:
    print(f"[!] {what} FAILED ({status}): {json.dumps(body)}", file=sys.stderr)
    sys.exit(1)


def create_object() -> None:
    body = {"data": {"api_slug": CLAIM_OBJECT, "singular_noun": "Claim", "plural_noun": "Claims"}}
    status, payload = req("POST", "/objects", body)
    if _ok(status):
        print(f"[+] object '{CLAIM_OBJECT}' created")
    elif status == 409:
        print(f"[=] object '{CLAIM_OBJECT}' already exists")
    else:
        die("create object", status, payload)


def attr(
    title: str,
    slug: str,
    type_: str,
    *,
    obj: str = CLAIM_OBJECT,
    description: str | None = None,
    is_unique: bool = False,
    is_multiselect: bool = False,
    config: dict | None = None,
    relationship: dict | None = None,
) -> None:
    data = {
        "title": title,
        "description": description,
        "api_slug": slug,
        "type": type_,
        "is_required": False,
        "is_unique": is_unique,
        "is_multiselect": is_multiselect,
        "config": config or {},
        "default_value": None,
    }
    if relationship is not None:
        data["relationship"] = relationship
    status, payload = req("POST", f"/objects/{obj}/attributes", {"data": data})
    if _ok(status):
        print(f"[+] {obj}.{slug} ({type_}) created")
    elif status == 409:
        print(f"[=] {obj}.{slug} already exists")
    else:
        die(f"create attr {obj}.{slug}", status, payload)


def option(attr_slug: str, title: str, obj: str = CLAIM_OBJECT) -> None:
    status, payload = req("POST", f"/objects/{obj}/attributes/{attr_slug}/options", {"data": {"title": title}})
    if _ok(status):
        print(f"      [+] option {attr_slug} = '{title}'")
    elif status == 409:
        print(f"      [=] option {attr_slug} = '{title}' exists")
    else:
        die(f"option {attr_slug}={title}", status, payload)


def pipeline_status(attr_slug: str, title: str) -> None:
    status, payload = req(
        "POST", f"/objects/{CLAIM_OBJECT}/attributes/{attr_slug}/statuses", {"data": {"title": title}}
    )
    if _ok(status):
        print(f"      [+] status {attr_slug} = '{title}'")
    elif status == 409:
        print(f"      [=] status {attr_slug} = '{title}' exists")
    else:
        die(f"status {attr_slug}={title}", status, payload)


def verify() -> None:
    status, payload = req("GET", f"/objects/{CLAIM_OBJECT}")
    if _ok(status):
        print(f"\nobject  {CLAIM_OBJECT}  object_id = {payload['data']['id']['object_id']}")
    else:
        print(f"\n[!] object '{CLAIM_OBJECT}' not found ({status})")
        return

    status, payload = req("GET", f"/objects/{CLAIM_OBJECT}/attributes?limit=100")
    if _ok(status):
        print(f"\n{CLAIM_OBJECT} attributes:")
        for a in payload.get("data", []):
            flags = []
            if a.get("is_unique"):
                flags.append("unique")
            if a.get("is_multiselect"):
                flags.append("multi")
            tag = f"  [{','.join(flags)}]" if flags else ""
            print(f"  {a['api_slug']:22s} {a['type']:16s} {a['id']['attribute_id']}{tag}")

    status, payload = req("GET", "/objects/companies/attributes?limit=100")
    if _ok(status):
        for a in payload.get("data", []):
            if a["api_slug"] == "ceiling":
                print(f"\ncompanies.ceiling  number  {a['id']['attribute_id']}")
                break


def main() -> None:
    if not TOKEN:
        die("ATTIO_API_KEY not set", 0, {"hint": "export ATTIO_API_KEY=...  (scope: object_configuration:read-write)"})

    if "--verify" in sys.argv:
        verify()
        return

    create_object()

    # --- text fields ---
    attr("Correlation ID", "correlation_id", "text", is_unique=True,
         description="Idempotency key; generated in n8n before claim creation so retries are idempotent.")
    attr("Order Number", "order_number", "text", description="Order number from the merchant OMS.")
    attr("Tracking Number", "tracking_number", "text", description="Primary courier barcode (T0.../H0...).")
    attr("Additional Tracking", "additional_tracking", "text",
         description="Further tracking numbers for multi-parcel claims (one per line).")
    attr("Delivery Postcode", "delivery_postcode", "text", description="Delivery destination postcode.")
    attr("Phone Number", "phone_number", "text", description="Contact phone supplied with this claim.")
    attr("Customer Comment", "customer_comment", "text", description="Customer's description of the issue.")
    attr("Fraud Flags", "fraud_flags", "text", description="Fraud signals raised during processing (one per line).")

    # --- select: courier ---
    attr("Courier", "courier", "select", description="Carrier handling the parcel.")
    for opt in ["Evri", "DPD", "Royal Mail", "Yodel", "Other"]:
        option("courier", opt)

    # --- select: claim type ---
    attr("Claim Type", "claim_type", "select", description="Loss vs damage.")
    for opt in ["Lost", "Damage"]:
        option("claim_type", opt)

    # --- status pipeline ---
    attr("Status", "status", "status", description="Claim lifecycle pipeline.")
    for stage in ["New", "Pending", "Raised", "Accepted", "Rejected", "DOR", "OnHold"]:
        pipeline_status("status", stage)

    # --- numbers ---
    attr("Parcel Count", "parcel_count", "number", description="Number of parcels covered by this claim.")
    attr("Cost Value", "cost_value", "number", description="Customer-stated cost of goods.")
    attr("Parcel Value", "parcel_value", "number",
         description="Ceiling actually submitted to Evri. SEPARATE from cost_value.")
    attr("Settlement Amount", "settlement_amount", "number", description="Set on Accepted; nullable otherwise.")
    attr("Risk Score", "risk_score", "number", description="Fraud score.")

    # --- relationships (with inverse 'claims' attribute on the related object) ---
    attr("Customer", "customer", "record-reference",
         description="The person who filed the claim (many claims to one person).",
         config={"record_reference": {"allowed_objects": ["people"]}},
         relationship={"object": "people", "title": "Claims", "api_slug": "claims", "is_multiselect": True})
    attr("Merchant", "merchant", "record-reference",
         description="The merchant the claim belongs to. Derived server-side in n8n, not customer-entered.",
         config={"record_reference": {"allowed_objects": ["companies"]}},
         relationship={"object": "companies", "title": "Claims", "api_slug": "claims", "is_multiselect": True})

    # --- companies.ceiling ---
    attr("Ceiling", "ceiling", "number", obj="companies",
         description="Per-merchant claim cap (e.g. £20 or £25). Drives parcel_value.")

    verify()


if __name__ == "__main__":
    main()
