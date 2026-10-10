from .test_foundation import payload


def test_unknown_origin_cannot_reset_or_modify_data(client):
    before = client.get("/api/dashboard").json()["balance"]
    for path, method in [("/api/demo/reset", "post"), ("/api/data", "delete"), ("/api/transactions", "post")]:
        response = getattr(client, method)(path, headers={"Origin": "https://unrelated.example"}, **({"json": payload()} if path.endswith("transactions") else {}))
        assert response.status_code == 403
    assert client.get("/api/dashboard").json()["balance"] == before


def test_csv_export_escapes_formula_text_and_private_headers(empty_client):
    c = empty_client
    assert c.post("/api/transactions", json=payload(description="=HYPERLINK(example)", merchant="@SUM(1)")).status_code == 201
    response = c.get("/api/export?format=csv")
    assert "'=HYPERLINK" in response.text and "'@SUM" in response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
