import csv
from datetime import date

from backend.app import finance
from backend.app.database import get_db
from backend.app.main import app
from backend.app.models import Transaction
from backend.app.transactions import fingerprint
from sqlalchemy.orm import Session


def test_csv_sniffer_error_returns_validation_response(client, monkeypatch):
    def fail(*args, **kwargs):
        raise csv.Error("Could not determine delimiter")
    monkeypatch.setattr(csv.Sniffer, "sniff", fail)
    response = client.post("/api/imports/preview", files={"file": ("bad.csv", b"broken\ncontent")})
    assert response.status_code == 422
    assert "delimiter" in response.json()["detail"]


def test_subscription_month_end_retains_observed_anchor(empty_client, monkeypatch):
    monkeypatch.setattr(finance, "today", lambda: date(2026, 3, 1))
    db = next(app.dependency_overrides[get_db]())
    with Session(db.bind) as session:
        for day in (date(2025, 12, 31), date(2026, 1, 31), date(2026, 2, 28)):
            session.add(Transaction(date=day, merchant="Monthly streaming membership", description="Streaming membership",
                                    amount_cents=-999, kind="expense", category="subscriptions",
                                    fingerprint=fingerprint(day, "Monthly streaming membership", -999)))
        session.commit()
    result = empty_client.get("/api/subscriptions").json()
    assert result["items"][0]["renewal"] == "2026-03-31"


def test_interest_whitespace_does_not_change_ranking(client):
    profile = client.get("/api/profile").json()
    profile["interests"] = "food,shopping,technology"
    client.put("/api/profile", json=profile)
    expected = client.get("/api/deals").json()["items"]
    profile["interests"] = " food, shopping, technology "
    client.put("/api/profile", json=profile)
    assert client.get("/api/deals").json()["items"] == expected


def test_assistant_never_silently_truncates_or_selects_ambiguous_amount(client):
    for question in ("Can I afford $1.001?", "Can I buy for $-5?", "Can I afford $150 or $200?", "Can I afford $0?"):
        response = client.post("/api/assistant", json={"question": question})
        assert response.status_code == 200
        assert response.json()["evidence"] == {}
    assert "outside" in client.post("/api/assistant", json={"question": "Can I buy $150 of stock?"}).json()["answer"]
    assert client.post("/api/assistant", json={"question": "Can I afford $1,250.75?"}).json()["evidence"]["purchase"] == 1250.75
