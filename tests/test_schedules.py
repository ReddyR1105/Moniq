from datetime import date

from backend.app.finance import advance_due


def schedule(**changes):
    return {"merchant": "Future tuition payment", "amount": 500, "category": "education", "kind": "expense",
            "next_due": "2026-10-12", "interval_days": 0, **changes}


def test_one_off_schedule_forecast_create_edit_delete(empty_client):
    c = empty_client
    result = c.post("/api/schedules", json=schedule())
    assert result.status_code == 201
    row = result.json()[0]
    forecast = c.get("/api/forecast").json()
    assert forecast["scheduled_expenses"] == 500 and forecast["projected_balance"] == -500
    assert len(forecast["events"]) == 1
    assert c.put(f"/api/schedules/{row['id']}", json=schedule(amount=400)).status_code == 200
    assert c.get("/api/forecast").json()["projected_balance"] == -400
    assert c.delete(f"/api/schedules/{row['id']}").status_code == 204
    assert c.get("/api/forecast").json()["scheduled_expenses"] == 0


def test_scheduled_income_repeat_and_validation(empty_client):
    c = empty_client
    assert c.post("/api/schedules", json=schedule(merchant="Tutoring pay", category="income", kind="income", amount=200, interval_days=14)).status_code == 201
    assert c.get("/api/forecast").json()["scheduled_income"] == 400
    assert c.post("/api/schedules", json=schedule(merchant="Tutoring pay", category="income", kind="income")).status_code == 409
    assert c.post("/api/schedules", json=schedule(category="income", kind="expense")).status_code == 422
    assert c.post("/api/schedules", json=schedule(next_due="2026-10-08")).status_code == 422
    assert c.post("/api/schedules", json=schedule(interval_days=-1)).status_code == 422


def test_calendar_month_anchor():
    february = advance_due(date(2026, 1, 31), 30, 31)
    assert february == date(2026, 2, 28)
    assert advance_due(february, 30, 31) == date(2026, 3, 31)


def test_incorrect_subscription_does_not_return_after_schedule_remove(client):
    first = client.get("/api/subscriptions").json()["items"][0]
    assert client.delete(f"/api/schedules/{first['id']}").status_code == 204
    item = next(i for i in client.get("/api/subscriptions").json()["items"] if i["id"] == first["id"])
    assert item["status"] == "incorrect"
    assert not any(e["merchant"] == first["merchant"] for e in client.get("/api/forecast").json()["events"])
