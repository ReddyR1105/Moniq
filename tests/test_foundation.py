import json


def payload(**changes):
    return {"date": "2026-10-09", "description": "Kroger grocery", "amount": 42.60, "kind": "expense", "category": "groceries", **changes}


def test_demo_and_health(client):
    assert client.get("/api/health").json()["model_loaded"]
    assert client.get("/api/profile").json()["university"] == "Georgia State University"
    assert len(client.get("/api/transactions").json()) > 70
    summary = client.get("/api/dashboard").json()
    assert summary["income"] > 0 and summary["expenses"] > 0
    assert len(summary["weekly_spending"]) == 7


def test_expense_income_refund_and_budget_math(empty_client):
    c = empty_client
    assert c.put("/api/budgets", json={"category": "groceries", "limit": 100}).status_code == 200
    assert c.post("/api/transactions", json=payload()).status_code == 201
    assert c.post("/api/transactions", json=payload(description="Campus payroll", amount=-200, kind="income", category="income")).status_code == 201
    assert c.post("/api/transactions", json=payload(description="Kroger refund", amount=-12.60, kind="refund")).status_code == 201
    d = c.get("/api/dashboard").json()
    assert d["balance"] == 170
    assert d["income"] == 200
    assert d["expenses"] == 30
    assert d["remaining_budget"] == 70
    assert c.get("/api/budgets").json()[0]["spent"] == 30


def test_duplicate_create_edit_and_delete(empty_client):
    c = empty_client
    first = c.post("/api/transactions", json=payload()).json()
    assert c.post("/api/transactions", json=payload()).status_code == 409
    other = c.post("/api/transactions", json=payload(description="Publix supermarket", amount=25)).json()
    assert c.put(f"/api/transactions/{other['id']}", json=payload()).status_code == 409
    changed = c.put(f"/api/transactions/{first['id']}", json=payload(category="food", amount=50))
    assert changed.json()["category"] == "food"
    assert c.get("/api/ml/metrics").json()["stored_corrections"] >= 1
    assert c.delete(f"/api/transactions/{first['id']}").status_code == 204
    assert c.delete(f"/api/transactions/{first['id']}").status_code == 404
    assert c.get("/api/dashboard").json()["balance"] == -25


def test_csv_mapping_duplicate_and_currency_formats(empty_client):
    c = empty_client
    content = b'Date,Details,Value,Type\n10/09/2026,Kroger grocery,"($42.60)",expense\n2026-10-08,Campus job payroll,"$1,200.00",income\nOct 7 2026,unused,1,income\n'
    # Unsupported dates reject the entire import before any row is written.
    mapping = {"date": "Date", "description": "Details", "amount": "Value", "kind": "Type"}
    bad = c.post("/api/imports/csv", files={"file": ("bank.csv", content, "text/csv")}, data={"mapping": json.dumps(mapping)})
    assert bad.status_code == 422
    assert c.get("/api/transactions").json() == []
    content = content.replace(b"Oct 7 2026,unused,1,income\n", b"")
    preview = c.post("/api/imports/preview", files={"file": ("bank.csv", content, "text/csv")}).json()
    assert preview["columns"] == ["Date", "Details", "Value", "Type"]
    one = c.post("/api/imports/csv", files={"file": ("bank.csv", content, "text/csv")}, data={"mapping": json.dumps(mapping)})
    assert one.json()["imported"] == 2
    two = c.post("/api/imports/csv", files={"file": ("bank.csv", content, "text/csv")}, data={"mapping": json.dumps(mapping)})
    assert two.json()["duplicates"] == 2
    assert c.get("/api/dashboard").json()["balance"] == 1157.4


def test_csv_separate_debit_credit_day_first(empty_client):
    content = b"When;What;Out;In\n08/10/2026;City transit pass;5.25;\n09/10/2026;Allowance;;100\n"
    mapping = {"date": "When", "description": "What", "debit": "Out", "credit": "In"}
    response = empty_client.post("/api/imports/csv", files={"file": ("statement.csv", content)}, data={"mapping": json.dumps(mapping), "day_first": "true"})
    assert response.json()["imported"] == 2
    assert empty_client.get("/api/dashboard").json()["balance"] == 94.75


def test_csv_positive_expense_and_refund(empty_client):
    content = b"date,description,amount,kind\n2026-10-09,Coffee,8.50,expense\n2026-10-08,Return,-3.50,refund\n"
    mapping = {"date": "date", "description": "description", "amount": "amount", "kind": "kind"}
    result = empty_client.post("/api/imports/csv", files={"file": ("bank.csv", content)}, data={"mapping": json.dumps(mapping), "convention": "positive_expense"})
    assert result.status_code == 200
    assert empty_client.get("/api/dashboard").json()["expenses"] == 5


def test_search_filters_and_persistence(client):
    rows = client.get("/api/transactions", params={"q": "Kroger", "category": "groceries"}).json()
    assert rows and all(r["category"] == "groceries" for r in rows)
    # Separate HTTP requests open separate SQLAlchemy sessions against a real SQLite file.
    row = client.post("/api/transactions", json=payload(description="Persistent test merchant", amount=2)).json()
    reread = client.get("/api/transactions", params={"q": "Persistent test merchant"}).json()
    assert reread[0]["id"] == row["id"]
    assert client.get("/api/transactions", params={"q": "%"}).json() == []


def test_invalid_inputs(client):
    for changes in [{"amount": 0}, {"amount": "NaN"}, {"amount": "1.001"}, {"description": "  "}, {"category": "unknown"}, {"date": "nonsense"}, {"kind": "refund", "category": "income"}]:
        assert client.post("/api/transactions", json=payload(**changes)).status_code == 422
    assert client.get("/api/transactions", params={"start": "oops"}).status_code == 422
    assert client.get("/api/transactions", params={"start": "2026-10-09", "end": "2026-10-01"}).status_code == 422
    assert client.post("/api/imports/preview", files={"file": ("bank.exe", b"x,y\n1,2")}).status_code == 422
    assert client.post("/api/imports/preview", files={"file": ("bank.csv", b"x" * (2 * 1024 * 1024 + 1))}).status_code == 422
    assert client.post("/api/imports/csv", files={"file": ("bank.csv", b"x,y\n1,2")}, data={"mapping": "[]"}).status_code == 422


def test_export_delete_reset(client):
    assert client.get("/api/export").json()["synthetic"]
    assert "date,description" in client.get("/api/export?format=csv").text
    assert client.delete("/api/data").status_code == 204
    assert client.get("/api/dashboard").json()["balance"] == 0
    assert client.get("/api/profile").json() is None
    assert client.post("/api/demo/reset").status_code == 200
    assert len(client.get("/api/transactions").json()) > 70
