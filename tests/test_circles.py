from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from backend.app import main
from backend.app.circles import allocate
from backend.app.models import Account


def circle(client, **changes):
    r = client.post(
        "/api/circles",
        json={
            "name": "Campus friends",
            "kind": "friends",
            "currency": "USD",
            "participants": ["Jordan"],
            **changes,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def expense(client, c, **changes):
    payload = {
        "title": "Shared dinner",
        "date": "2026-10-09",
        "amount": "60.00",
        "payer_id": c["members"][0]["id"],
        "method": "equal",
        "shares": {str(m["id"]): "0" for m in c["members"]},
        **changes,
    }
    r = client.post(f"/api/circles/{c['id']}/expenses", json=payload)
    assert r.status_code == 201, r.text
    return r.json()["expenses"][0], payload


@pytest.mark.parametrize("total,count", [(1, 3), (100, 3), (4001, 7), (99999999, 19)])
def test_equal_every_cent_allocated(total, count):
    result = allocate(total, "equal", {m: Decimal(0) for m in range(count)})
    assert sum(result.values()) == total
    assert max(result.values()) - min(result.values()) <= 1
    assert result == allocate(total, "equal", {m: Decimal(0) for m in reversed(range(count))})


def test_linked_cash_share_partial_repayment_idempotency(empty_client):
    client = empty_client
    with Session(main.engine) as db:
        db.get(Account, 1).opening_balance_cents = 10000
        db.commit()
    t = client.post(
        "/api/transactions",
        json={"date": "2026-10-09", "description": "Chick-fil-A", "amount": "60.00", "category": "food"},
    ).json()
    c = circle(client)
    e, payload = expense(client, c, transaction_id=t["id"])
    data = client.get("/api/dashboard").json()
    assert (data["balance"], data["expenses"], data["cash_expenses"], data["income"]) == (40, 30, 60, 0)
    assert client.get("/api/circles").json()[0]["receivable_cents"] == 3000
    assert client.delete(f"/api/transactions/{t['id']}").status_code == 409
    assert (
        client.put(
            f"/api/transactions/{t['id']}",
            json={"date": "2026-10-09", "description": "Chick-fil-A", "amount": "20.00", "category": "food"},
        ).status_code
        == 409
    )
    assert client.post(f"/api/circles/{c['id']}/expenses", json=payload).status_code == 409
    request = {
        "member_id": c["members"][1]["id"],
        "date": "2026-10-09",
        "amount": "10.00",
        "confirmed": True,
        "request_key": str(uuid4()),
        "record_cash": True,
        "account_id": 1,
    }
    url = f"/api/circles/expenses/{e['id']}/settlements"
    assert client.post(url, json=request).status_code == 201
    assert client.post(url, json=request).json()["duplicate"] is True
    assert client.get("/api/dashboard").json()["balance"] == 50
    assert client.get("/api/circles").json()[0]["receivable_cents"] == 2000
    assert (
        client.post(url, json={**request, "amount": "20.01", "request_key": str(uuid4())}).status_code == 422
    )
    assert (
        client.post(url, json={**request, "amount": "20.00", "request_key": str(uuid4())}).status_code == 201
    )
    data = client.get("/api/dashboard").json()
    assert (data["balance"], data["expenses"], data["income"]) == (70, 30, 0)
    assert client.get("/api/circles").json()[0]["receivable_cents"] == 0
    assert len(client.get("/api/transactions").json()) == 3
    assert client.delete(f"/api/circles/expenses/{e['id']}").status_code == 409


@pytest.mark.parametrize(
    "method,shares,expected",
    [
        ("amount", ["10.01", "20.00", "29.99"], [1001, 2000, 2999]),
        ("percentage", ["33.33", "33.33", "33.34"], [2000, 2000, 2000]),
    ],
)
def test_custom_percent_multi_member_splits(empty_client, method, shares, expected):
    c = circle(empty_client, participants=["Jordan", "Sam"])
    e, _ = expense(
        empty_client, c, method=method, shares={str(m["id"]): v for m, v in zip(c["members"], shares)}
    )
    assert [s["share_cents"] for s in e["shares"]] == expected
    assert sum(s["share_cents"] for s in e["shares"]) == 6000
    assert empty_client.get("/api/dashboard").json()["expenses"] == expected[0] / 100
    assert empty_client.get("/api/dashboard").json()["balance"] == 0


def test_percentage_rounding_exclusion_edit_delete_and_validation(empty_client):
    c = circle(empty_client, participants=["Jordan", "Sam"])
    ids = [m["id"] for m in c["members"]]
    e, payload = expense(
        empty_client, c, amount="0.01", method="percentage", shares={str(ids[0]): "50", str(ids[1]): "50"}
    )
    assert [s["share_cents"] for s in e["shares"]] == [1, 0]
    url = f"/api/circles/expenses/{e['id']}"
    assert (
        empty_client.put(
            url,
            json={
                **payload,
                "amount": "10.00",
                "method": "amount",
                "shares": {str(ids[0]): "3.00", str(ids[1]): "7.00"},
            },
        ).status_code
        == 200
    )
    assert empty_client.get("/api/dashboard").json()["expenses"] == 3
    assert empty_client.put(url, json={**payload, "shares": {str(ids[0]): "101"}}).status_code == 422
    assert empty_client.delete(url).status_code == 200
    assert empty_client.get("/api/dashboard").json()["expenses"] == 0
    assert empty_client.get("/api/circles").json()[0]["expenses"] == []


def test_paid_by_other_payable_and_outgoing_settlement(empty_client):
    c = circle(empty_client)
    e, _ = expense(empty_client, c, payer_id=c["members"][1]["id"])
    assert empty_client.get("/api/circles").json()[0]["payable_cents"] == 3000
    assert empty_client.get("/api/dashboard").json()["expenses"] == 30
    r = empty_client.post(
        f"/api/circles/expenses/{e['id']}/settlements",
        json={
            "member_id": c["members"][0]["id"],
            "amount": "30.00",
            "date": "2026-10-09",
            "confirmed": True,
            "record_cash": True,
            "account_id": 1,
            "request_key": str(uuid4()),
        },
    )
    assert r.status_code == 201, r.text
    data = empty_client.get("/api/dashboard").json()
    assert (data["balance"], data["expenses"], data["income"]) == (-30, 30, 0)


def test_existing_incoming_transaction_is_reused_only_after_confirmation(empty_client):
    c = circle(empty_client)
    e, _ = expense(empty_client, c)
    tx = empty_client.post(
        "/api/transactions",
        json={"date": "2026-10-09", "description": "Jordan repayment", "amount": "30.00", "kind": "income"},
    ).json()
    payload = {
        "member_id": c["members"][1]["id"],
        "amount": "30.00",
        "date": "2026-10-09",
        "transaction_id": tx["id"],
        "request_key": str(uuid4()),
    }
    url = f"/api/circles/expenses/{e['id']}/settlements"
    assert empty_client.post(url, json=payload).status_code == 422
    assert empty_client.post(url, json={**payload, "confirmed": True}).status_code == 201
    assert len(empty_client.get("/api/transactions").json()) == 1
    data = empty_client.get("/api/dashboard").json()
    assert (data["balance"], data["income"], data["expenses"]) == (30, 0, 30)


def test_currencies_and_circle_members_cannot_mix(empty_client):
    c = circle(empty_client, currency="EUR")
    expense(empty_client, c)
    data = empty_client.get("/api/dashboard").json()
    assert data["expenses"] == 0
    assert data["circles"]["currencies"]["EUR"]["receivable_cents"] == 3000
    other = circle(empty_client, name="Other circle", participants=["Sam"])
    r = empty_client.post(
        f"/api/circles/{c['id']}/expenses",
        json={
            "title": "Dinner",
            "date": "2026-10-09",
            "amount": "10.00",
            "payer_id": other["members"][0]["id"],
            "shares": {str(c["members"][0]["id"]): "0"},
        },
    )
    assert r.status_code == 422


def test_shared_insights_are_grounded_and_reset_export_cover_ledger(empty_client):
    c = circle(empty_client)
    expense(empty_client, c, title="Shared rent", category="rent", amount="1000.00", recurring=True)
    expense(
        empty_client, c, title="Shared subscription", category="subscriptions", amount="20.00", recurring=True
    )
    result = empty_client.post(
        "/api/assistant", json={"question": "How much should I reserve for shared rent?"}
    ).json()
    assert result["evidence"]["next_month_rent_reserve_cents"] == 50000
    export = empty_client.get("/api/export").json()
    assert len(export["circle_expenses"]) == 2 and len(export["ledger_audits"]) >= 3
    assert empty_client.post("/api/demo/reset").status_code == 200
    assert empty_client.get("/api/circles").json() == []


def test_add_participants_preserves_existing_allocations(empty_client):
    c = circle(empty_client)
    e, _ = expense(empty_client, c)
    url = f"/api/circles/{c['id']}/members"
    result = empty_client.post(url, json={"name": "Sam"})
    assert result.status_code == 201
    assert len(result.json()["members"]) == 3
    assert result.json()["expenses"][0]["shares"] == e["shares"]
    assert empty_client.post(url, json={"name": "sam"}).status_code == 422
    assert empty_client.post(url, json={"name": " "}).status_code == 422


def test_repayment_csv_types_preserve_cash_without_income_or_spending(empty_client):
    import csv
    import io
    from backend.app.transactions import csv_payloads, read_csv

    frame = read_csv(
        b"date,description,amount,kind\n2026-10-09,Jordan repayment,30.00,reimbursement\n2026-10-09,Rent repayment,-10.00,settlement\n",
        "repayments.csv",
    )
    mapping = {"date": "date", "description": "description", "amount": "amount", "kind": "kind"}
    for p in csv_payloads(frame, mapping, "negative_expense"):
        assert empty_client.post("/api/transactions", json=p.model_dump(mode="json")).status_code == 201
    data = empty_client.get("/api/dashboard").json()
    assert (data["balance"], data["income"], data["expenses"]) == (20, 0, 0)
    assert len(empty_client.get("/api/transactions?kind=reimbursement").json()) == 1
    exported = list(csv.DictReader(io.StringIO(empty_client.get("/api/export?format=csv").text)))
    assert {t["kind"] for t in exported} == {"reimbursement", "settlement"}
