"""Exercise the actual session middleware, database routing and sample policy."""
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.app import main
from backend.app.demo_sessions import COOKIE_NAME, DemoSessionStore


@pytest.fixture
def public_client(tmp_path, monkeypatch, ml):
    monkeypatch.setattr(main, "PUBLIC_DEMO", True)
    monkeypatch.setattr(main, "COOKIE_SECURE", False)
    monkeypatch.setattr(main, "PUBLIC_ORIGIN", "http://testserver")
    monkeypatch.setattr(main, "RUNTIME", tmp_path)
    monkeypatch.setattr(main, "Classifier", lambda **kwargs: ml)
    with TestClient(main.app) as client:
        yield client


def test_circles_rules_and_controlled_scenario_are_visitor_isolated(public_client):
    client=public_client
    a,b=new_visitor(client),new_visitor(client)
    baseline=client.get("/api/dashboard",headers=b).json()["balance"]
    assert client.post("/api/upgrade-demo/start",headers=a).status_code == 200
    assert client.post("/api/upgrade-demo/alert",headers=a).json()["auto_approved"] is True
    assert client.get("/api/dashboard",headers=a).json()["balance"] == 60
    assert client.get("/api/dashboard",headers=b).json()["balance"] == baseline
    c=client.post("/api/circles",headers=a,json={"name":"Campus friends","participants":["Jordan"]}).json()
    payload={"title":"Shared dinner","date":client.get('/api/dashboard',headers=a).json()['as_of'],"amount":"40.00","payer_id":c['members'][0]['id'],"transaction_id":1,"shares":{str(m['id']):"0" for m in c['members']}}
    assert client.post(f"/api/circles/{c['id']}/expenses",headers=b,json=payload).status_code == 404
    assert client.post(f"/api/circles/{c['id']}/expenses",headers=a,json=payload).status_code == 201
    assert client.get('/api/circles',headers=b).json() == []
    assert client.get('/api/smartapprove/rules',headers=b).json() == []
    assert client.get('/api/smartapprove/summary',headers=b).json()['auto_approved'] == 0
    assert client.app.state.personal_engine is None and client.app.state.gmail is None
    assert client.post('/api/circles',headers=a,json={"name":"My personal circle","participants":["Private Name"]}).status_code == 403


def new_visitor(client):
    client.cookies.clear()
    response = client.get("/api/config")
    assert response.status_code == 200 and response.json()["public_demo"]
    cookie = client.cookies.get(COOKIE_NAME)
    client.cookies.clear()
    return {"cookie": f"{COOKIE_NAME}={cookie}"}


def test_public_sessions_cannot_access_gmail_or_personal_databases(public_client, monkeypatch):
    from backend.app import gmail_routes

    def forbidden(*args, **kwargs):
        pytest.fail("Public requests must not instantiate a Gmail manager or read personal data.")

    monkeypatch.setattr(gmail_routes, "manager", forbidden)
    for path in ("/api/gmail/status", "/api/gmail/accounts", "/api/gmail/items", "/api/gmail/callback?code=synthetic"):
        assert public_client.get(path, headers={"Cookie": "moniq_workspace=personal"}).status_code == 403
    for path in ("/api/gmail/connect", "/api/gmail/sync", "/api/gmail/disconnect", "/api/workspace"):
        assert public_client.post(path, json={"workspace": "personal"}).status_code == 403
    assert public_client.app.state.personal_engine is None


def test_visitors_purchase_reset_delete_and_export_are_isolated(public_client):
    client = public_client
    a, b = new_visitor(client), new_visitor(client)
    assert a != b
    original = client.get("/api/dashboard", headers=b).json()
    text = client.get("/api/notifications/examples", headers=a).json()["examples"][0]
    payload = client.post("/api/notifications/parse", headers=a, json={"text": text}).json()
    payload["notification_text"] = text
    purchase = client.post("/api/transactions", headers=a, json=payload)
    assert purchase.status_code == 201
    assert purchase.json()["amount"] == -15.75
    assert client.get("/api/dashboard", headers=a).json() != original
    assert client.get("/api/dashboard", headers=b).json() == original
    assert client.delete(f'/api/transactions/{purchase.json()["id"]}', headers=b).status_code == 404
    assert client.post("/api/transactions", headers=a, json=payload).status_code == 409
    assert client.put("/api/budgets", headers=b, json={"category": "food", "period": "monthly", "limit": 260}).status_code == 200
    b_changed = client.get("/api/export", headers=b).json()
    assert client.post("/api/demo/reset", headers=a).status_code == 200
    assert client.delete("/api/data", headers=a).status_code == 204
    assert client.get("/api/profile", headers=a).json() is None
    assert client.get("/api/export", headers=b).json() == b_changed
    assert client.get("/api/profile", headers=b).json()["name"] == "Alex Morgan"


def test_public_policy_blocks_private_text_and_uploads_but_samples_work(public_client):
    client = public_client
    visitor = new_visitor(client)
    assert client.post("/api/imports/preview", headers=visitor, files={"file": ("private.csv", b"secret")}).status_code == 403
    assert client.post("/api/notifications/parse", headers=visitor, json={"text": "My private statement"}).status_code == 403
    assert client.post("/api/assistant", headers=visitor, json={"question": "My account number is private"}).status_code == 403
    profile = client.get("/api/profile", headers=visitor).json()
    profile["name"] = "Private visitor"
    assert client.put("/api/profile", headers=visitor, json=profile).status_code == 403
    assert client.post("/api/ml/retrain", headers=visitor).status_code == 403
    sample = client.post("/api/demo/import-sample", headers=visitor)
    assert sample.status_code == 200 and sample.json()["imported"] > 0
    repeat = client.post("/api/demo/import-sample", headers=visitor).json()
    assert repeat["imported"] == 0 and repeat["duplicates"] > 0
    for question in main.check_question.__globals__["ASSISTANT_QUESTIONS"]:
        assert client.post("/api/assistant", headers=visitor, json={"question": question}).status_code == 200


def test_cookies_origins_expiry_and_capacity(public_client, monkeypatch):
    client = public_client
    response = client.get("/api/config")
    assert "HttpOnly" in response.headers["set-cookie"] and "SameSite=lax" in response.headers["set-cookie"]
    token = client.cookies.get(COOKIE_NAME)
    assert len(token) == 64
    monkeypatch.setattr(main, "COOKIE_SECURE", True)
    assert "; Secure" in client.get("/api/config").headers["set-cookie"]
    monkeypatch.setattr(main, "COOKIE_SECURE", False)
    client.cookies.clear()
    client.cookies.set(COOKIE_NAME, token, domain="testserver.local", path="/")
    assert client.get("/api/dashboard", headers={"Origin": "https://foreign.example"}).status_code == 403
    assert client.get("/api/config", headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
    assert client.post("/api/assistant", content="x" * 8193).status_code == 413
    store = main.app.state.demo_store
    store.sessions[token].last_seen = time.monotonic() - store.ttl - 1
    assert client.get("/api/dashboard").status_code == 401
    assert client.get("/api/config").status_code == 200
    assert client.cookies.get(COOKIE_NAME) != token
    store.maximum = len(store.sessions)
    client.cookies.clear()
    assert client.get("/api/config").status_code == 503


def test_store_concurrent_bootstrap_restart_and_active_expiry(tmp_path):
    store = DemoSessionStore(tmp_path, ttl_seconds=1, maximum=4)
    directory = store.root
    with ThreadPoolExecutor(max_workers=4) as pool:
        tokens = list(pool.map(lambda _: store.bootstrap(), range(4)))
    assert len(set(tokens)) == 4
    assert len({store.sessions[t].path for t in tokens}) == 4
    with store.lease(tokens[0]):
        store.sessions[tokens[0]].last_seen -= 10
        store._prune()
        assert tokens[0] in store.sessions
    store.close()
    assert not directory.exists()
    restarted = DemoSessionStore(tmp_path)
    try:
        with pytest.raises(HTTPException) as expired:
            with restarted.lease(tokens[0]):
                pass
        assert expired.value.status_code == 401
    finally:
        restarted.close()


def test_public_profile_goals_schedule_corrections_and_model_are_independent(public_client):
    client = public_client
    a, b = new_visitor(client), new_visitor(client)
    baseline = client.get("/api/ml/metrics", headers=b).json()
    profile = client.get("/api/profile", headers=a).json()
    profile.update(allowance=700, university="Georgia Tech", interests="food,groceries")
    assert client.put("/api/profile", headers=a, json=profile).status_code == 200
    assert client.get("/api/profile", headers=b).json()["university"] == "Georgia State University"
    assert client.put("/api/goals/1", headers=a, json={"name": "Emergency fund", "target": 2000, "saved": 500}).status_code == 200
    assert client.put("/api/goals/1", headers=a, json={"name": "Private personal name", "target": 2000, "saved": 500}).status_code == 403
    schedule = client.get("/api/schedules", headers=a).json()[0]
    schedule["amount"] += 10
    assert client.put(f'/api/schedules/{schedule["id"]}', headers=a, json=schedule).status_code == 200
    row = client.get("/api/transactions", headers=a).json()[0]
    row["category"] = "miscellaneous" if row["category"] != "miscellaneous" else "food"
    assert client.put(f'/api/transactions/{row["id"]}', headers=a, json=row).status_code == 200
    assert client.get("/api/ml/metrics", headers=a).json()["stored_corrections"] == 1
    assert client.get("/api/ml/metrics", headers=b).json() == baseline
    prediction = {"description": "Unknown synthetic demo purchase"}
    assert client.post("/api/classify", headers=a, json=prediction).json() == client.post("/api/classify", headers=b, json=prediction).json()


def test_public_database_helpers_fail_closed_without_a_visitor_lease(public_client):
    from backend.app.database import get_db, personal_engine, scenario_engine
    from starlette.requests import Request

    app = public_client.app
    request = Request({"type": "http", "app": app, "headers": [(b"cookie", b"moniq_workspace=personal")]})
    for helper in (personal_engine, scenario_engine):
        with pytest.raises(HTTPException) as denied:
            helper(app)
        assert denied.value.status_code == 403
    with pytest.raises(HTTPException) as denied:
        next(get_db(request))
    assert denied.value.status_code == 401
    assert app.state.personal_engine is None and app.state.scenario_engine is None


def test_public_rejections_and_success_have_private_cache_and_security_headers(public_client, monkeypatch):
    client = public_client
    visitor = new_visitor(client)
    for path, code, headers in [("/api/dashboard", 200, visitor), ("/api/gmail/status", 403, visitor),
                                ("/api/dashboard", 403, {**visitor, "Origin": "https://foreign.example"})]:
        response = client.get(path, headers=headers)
        assert response.status_code == code
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert "connect-src 'self'" in response.headers["content-security-policy"]
        assert response.headers["permissions-policy"] == "camera=(), microphone=(), geolocation=(), payment=()"
    monkeypatch.setattr(main, "PUBLIC_ORIGIN", "https://moniq.example.test")
    response = client.get("/api/health")
    assert response.headers["strict-transport-security"] == "max-age=31536000"


def test_public_configuration_ignores_accidentally_present_gmail_secrets(tmp_path):
    import json
    import os
    import subprocess
    import sys

    environment = {**os.environ, "MONIQ_PUBLIC_DEMO": "true", "MONIQ_GMAIL_DISABLED": "false",
                   "GMAIL_CLIENT_ID": "synthetic-id", "GMAIL_CLIENT_SECRET": "synthetic-secret",
                   "GMAIL_TOKEN_ENCRYPTION_KEY": "synthetic-key"}
    result = subprocess.run([sys.executable, "-c", "import json; from backend.app import config; print(json.dumps([config.GMAIL_DISABLED, bool(config.GMAIL_CLIENT_ID), bool(config.GMAIL_CLIENT_SECRET), bool(config.GMAIL_TOKEN_ENCRYPTION_KEY)]))"], env=environment, check=True, capture_output=True, text=True)
    assert json.loads(result.stdout) == [True, False, False, False]
