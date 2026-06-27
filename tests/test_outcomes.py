"""Outcome ingestion: in-memory path + Attio-hydration fallback (restart-safe)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.deps import get_deps
from app.main import app

client = TestClient(app)


def _process_to_raised(tracking: str, corr: str) -> None:
    # Unknown tracking -> AfterShip/Tavily unset -> stub -> proceed -> Pending -> Raised
    r = client.post(
        f"/claims/{corr}/process",
        json={
            "courier": "Evri",
            "claim_type": "Lost",
            "tracking_number": tracking,
            "order_number": "ORD-T",
            "delivery_postcode": "M1 4WP",
            "cost_value": 40,
            "parcel_value": 25,
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "Raised"


def test_outcome_accept_in_memory():
    _process_to_raised("T0OUTCOME001", "clm-out-1")
    r = client.post(
        "/outcomes/ingest",
        json={"barcode": "T0OUTCOME001", "claim_status": "Accepted (DA1)"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "Accepted"
    assert body["settlement_amount"] == 25.0  # defaults to parcel_value (ceiling)


def test_outcome_reject_in_memory():
    _process_to_raised("T0OUTCOME002", "clm-out-2")
    r = client.post(
        "/outcomes/ingest",
        json={"barcode": "T0OUTCOME002", "claim_status": "Rejected (OOT)"},
    )
    assert r.json()["status"] == "Rejected"


def test_outcome_hydrates_from_attio(monkeypatch):
    # A barcode the in-memory repo has never seen -> must hydrate from Attio.
    fake = {
        "correlation_id": "clm-hydrated-9",
        "tracking_number": "T0HYDRATE9",
        "status": "Raised",
        "claim_type": "Lost",
        "parcel_value": 25,
        "cost_value": 50,
        "delivery_postcode": "BS1 5TR",
        "order_number": "ORD-H9",
    }
    monkeypatch.setattr(get_deps().attio, "get_claim_by_tracking", lambda tn: fake)

    r = client.post(
        "/outcomes/ingest",
        json={"barcode": "T0HYDRATE9", "claim_status": "Accepted (DA1)", "settlement_amount": 25},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "Accepted"
    assert body["correlation_id"] == "clm-hydrated-9"
    assert body["settlement_amount"] == 25.0
