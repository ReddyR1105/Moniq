from datetime import date

from backend.app.ml import Classifier, synthetic_data
from backend.app.models import Account, Base, RecurringPayment, Transaction
from backend.app.transactions import fingerprint
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

def test_classifier_actual_pipeline_saved_and_held_out(ml):
    assert ml.classify("Chick-fil-A restaurant")["category"] == "food"
    assert ml.classify("Kroger grocery")["category"] == "groceries"
    assert ml.classify("Campus job payroll")["category"] == "income"
    assert ml.classify("zxqv unknown 999")["needs_review"]
    assert ml.classify("zxqv unknown 999")["category"] == "miscellaneous"
    loaded = Classifier(ml.model_dir)
    assert loaded.classify("Kroger grocery") == ml.classify("Kroger grocery")
    frame = synthetic_data()
    assert not set(frame[frame.split == "train"].merchant_family) & set(frame[frame.split == "test"].merchant_family)
    assert ml.report["test_rows"] == 264
    assert 0 <= ml.report["accuracy"] <= 1
    assert "macro avg" in ml.report["classification_report"]


def test_notification_parse_confirm_updates_budget(client):
    before = client.get("/api/dashboard").json()
    text = "Your card ending in 1234 was charged $18.75 at Chick-fil-A."
    response = client.post("/api/notifications/parse", json={"text": text})
    assert response.status_code == 200
    parsed = response.json()
    assert parsed["merchant"] == "Chick-fil-A"
    assert parsed["amount"] == 18.75 and parsed["category"] == "food"
    assert client.get("/api/dashboard").json()["balance"] == before["balance"]
    assert client.post("/api/transactions", json=parsed).status_code == 201
    after = client.get("/api/dashboard").json()
    assert round(before["balance"] - after["balance"], 2) == 18.75
    assert round(after["expenses"] - before["expenses"], 2) == 18.75
    assert client.post("/api/transactions", json=parsed).status_code == 409


def test_notifications_refunds_income_dates_and_ambiguous(client):
    refund = client.post("/api/notifications/parse", json={"text": "Refund of $15.00 from Target clothing on 2026-10-08."}).json()
    assert refund["kind"] == "refund" and refund["date"] == "2026-10-08"
    income = client.post("/api/notifications/parse", json={"text": "Payroll deposit of $620.00 from Campus job payroll."}).json()
    assert income["kind"] == "income" and income["category"] == "income"
    for text in ["Card charged without amount", "Charged $10 at A and $12 at B", "Balance $100", "Charged $0 at Cafe"]:
        assert client.post("/api/notifications/parse", json={"text": text}).status_code == 422


def test_budget_update_immediate_and_weekly(client):
    result = client.put("/api/budgets", json={"category": "food", "period": "weekly", "limit": 1}).json()
    assert next(b for b in result if b["category"] == "food" and b["period"] == "weekly")["overspent"]
    assert client.get("/api/dashboard").json()["insights"]["warnings"]
    assert client.put("/api/budgets", json={"category": "food", "limit": "1.001"}).status_code == 422


def test_scenario_exact_deltas_delay_and_savings_cap(client):
    base = client.get("/api/forecast").json()
    assert len(base["timeline"]) == 31
    result = client.post("/api/scenarios", json={"purchase": 150, "savings": 50, "extra_income": 200}).json()
    assert result["difference"] == 100
    delay = client.post("/api/scenarios", json={"purchase": 500, "delay_days": 31}).json()
    assert delay["difference"] == 0 and not delay["scenario"]["purchase_in_horizon"]
    cap = client.post("/api/scenarios", json={"savings": 999999}).json()
    assert cap["scenario"]["applied_savings"] == base["discretionary_spending"]
    assert client.post("/api/scenarios", json={"purchase": -1}).status_code == 422


def test_forecast_known_schedule_counted_once(empty_client):
    from backend.app.main import app
    from backend.app.database import get_db
    db = next(app.dependency_overrides[get_db]())
    # Use a fresh context because get_db's generator above closes its session after next.
    with Session(db.bind) as session:
        session.get(Account, 1).opening_balance_cents = 100000
        session.add(RecurringPayment(merchant="Campus apartment rent", amount_cents=50000, category="rent", next_due=date(2026, 10, 10), status="confirmed"))
        session.add(RecurringPayment(merchant="Paycheck", amount_cents=20000, category="income", kind="income", next_due=date(2026, 10, 15), interval_days=30, status="confirmed"))
        day = date(2026, 10, 1)
        session.add(Transaction(date=day, merchant="Campus apartment rent", description="Rent", amount_cents=-50000, category="rent", kind="expense", fingerprint=fingerprint(day, "Rent", -50000)))
        session.commit()
    result = empty_client.get("/api/forecast").json()
    assert result["current_balance"] == 500
    assert result["discretionary_spending"] == 0
    assert result["scheduled_expenses"] == 500
    assert result["scheduled_income"] == 200
    assert result["projected_balance"] == 200


def test_subscription_confirmation_and_exclusion(client):
    result = client.get("/api/subscriptions").json()
    assert len(result["items"]) == 3
    assert result["monthly_total"] == 41.47
    item = result["items"][0]
    assert item["evidence_count"] >= 3
    assert client.put(f"/api/subscriptions/{item['id']}", json={"status": "confirmed"}).status_code == 200
    changed = client.put(f"/api/subscriptions/{item['id']}", json={"status": "incorrect"}).json()
    assert round(changed["monthly_total"], 2) == round(41.47 - item["amount"], 2)
    assert any(i["status"] == "incorrect" for i in client.get("/api/subscriptions").json()["items"])


def test_deals_rank_eligibility_budget_and_sample_labels(client):
    result = client.get("/api/deals").json()
    assert result["items"]
    assert all(r["verification"] == "synthetic sample" for r in result["items"])
    assert result["items"] == sorted(result["items"], key=lambda r: (-r["score"], r["id"]))
    assert all(r["merchant"] != "Tech Workshop" for r in result["items"])
    profile = client.get("/api/profile").json()
    profile["student_verified"] = False
    assert client.put("/api/profile", json=profile).status_code == 200
    assert client.get("/api/deals").json()["items"] == []


def test_assistant_evidence_and_unsupported_scope(client):
    result = client.post("/api/assistant", json={"question": "How much did I spend this week?"}).json()
    assert result["mode"] == "local"
    assert result["evidence"]["calendar_week_spending"] == client.get("/api/dashboard").json()["week_total"]
    afford = client.post("/api/assistant", json={"question": "Can I afford a $150 purchase?"}).json()
    scenario = client.post("/api/scenarios", json={"purchase": 150}).json()
    assert afford["evidence"]["projected_balance"] == scenario["scenario"]["projected_balance"]
    assert "outside" in client.post("/api/assistant", json={"question": "Which stock should I invest in?"}).json()["answer"]


def test_settings_allowance_forecast_goals(client):
    profile = client.get("/api/profile").json()
    profile["allowance"] = 800
    assert client.put("/api/profile", json=profile).json()["allowance"] == 800
    allowance = next(e for e in client.get("/api/forecast").json()["events"] if e["merchant"] == "Family allowance")
    assert allowance["amount"] == 800
    assert client.put("/api/goals/1", json={"name": "Emergency fund", "target": 2000, "saved": 500}).json()[0]["target"] == 2000


def test_persistence_survives_engine_restart(tmp_path):
    location = f"sqlite:///{(tmp_path / 'persistent.db').as_posix()}"
    engine = create_engine(location)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Account(id=1, opening_balance_cents=12345))
        db.commit()
    engine.dispose()
    restarted = create_engine(location)
    with Session(restarted) as db:
        assert db.get(Account, 1).opening_balance_cents == 12345
    restarted.dispose()
