"""Real OAuth/route code exercised against synthetic, mocked Google responses."""

import base64
import hashlib
import json
import time
from datetime import date, datetime
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

import httpx
import pytest
from authlib.integrations.httpx_client import OAuth2Client
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app import config, database, finance, gmail_parser, gmail_service, main, notifications, seed
from backend.app.gmail_parser import parse_financial_email
from backend.app.gmail_service import STATE_COOKIE, TOKEN_URL, TokenVault


def email(identifier, body, subject="Financial alert", mime="text/plain", **extra):
    return {
        "id": identifier,
        "labelIds": ["INBOX"],
        "internalDate": str(
            int(datetime(2026, 10, 9, 12, tzinfo=ZoneInfo("America/New_York")).timestamp() * 1000)
        ),
        "payload": {
            "mimeType": mime,
            "headers": [
                {"name": "Subject", "value": subject},
                {"name": "From", "value": "Synthetic Bank <alerts@example.test>"},
            ],
            "body": {"data": base64.urlsafe_b64encode(body.encode()).decode().rstrip("=")},
        },
        **extra,
    }


class Google:
    def __init__(self):
        self.requests = []
        self.messages = {}
        self.scope = config.GMAIL_SCOPE
        self.refresh_ok = True
        self.revoke_ok = True
        self.api_status = 200
        self.next_page = None

    def respond(self, request):
        self.requests.append(request)
        assert request.url.host in {"oauth2.googleapis.com", "gmail.googleapis.com"}
        if str(request.url) == TOKEN_URL:
            data = parse_qs(request.content.decode())
            if data["grant_type"] == ["authorization_code"]:
                assert data["code"] == ["synthetic-code"]
                assert len(data["code_verifier"][0]) >= 43
                assert data["redirect_uri"] == [config.GMAIL_REDIRECT_URI]
                assert data["client_secret"] == ["synthetic-client-secret"]
            elif not self.refresh_ok:
                return httpx.Response(400, json={"error": "invalid_grant"})
            return httpx.Response(
                200,
                json={
                    "access_token": "synthetic-access",
                    "refresh_token": "synthetic-refresh",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                    "scope": self.scope,
                },
            )
        if request.url.path.endswith("/revoke"):
            return httpx.Response(200 if self.revoke_ok else 503)
        assert request.headers["Authorization"] == "Bearer synthetic-access"
        if self.api_status != 200:
            return httpx.Response(self.api_status, json={"error": "synthetic failure"})
        if request.url.path.endswith("/profile"):
            return httpx.Response(200, json={"emailAddress": "synthetic-user@example.test"})
        if request.url.path.endswith("/messages"):
            assert "newer_than:30d" in request.url.params["q"]
            assert request.url.params["includeSpamTrash"] == "false"
            response = {"messages": [{"id": identifier} for identifier in self.messages]}
            if self.next_page:
                response["nextPageToken"] = self.next_page
            return httpx.Response(200, json=response)
        assert request.url.params["format"] == "full"
        return httpx.Response(200, json=self.messages[request.url.path.rsplit("/", 1)[1]])


@pytest.fixture
def gmail(tmp_path, monkeypatch, ml):
    engine = create_engine(
        f"sqlite:///{tmp_path.as_posix()}/demo.db", connect_args={"check_same_thread": False}
    )
    monkeypatch.setattr(main, "engine", engine)
    monkeypatch.setattr(database, "SessionLocal", sessionmaker(bind=engine))
    monkeypatch.setattr(main, "Classifier", lambda: ml)
    monkeypatch.setattr(main, "PUBLIC_DEMO", False)
    for module in (config, finance, seed, notifications, gmail_parser):
        monkeypatch.setattr(module, "today", lambda: date(2026, 10, 9))
    monkeypatch.setattr(config, "RUNTIME", tmp_path)
    monkeypatch.setattr(config, "GMAIL_TOKEN_DIR", tmp_path / "gmail")
    monkeypatch.setattr(config, "PERSONAL_DATABASE_URL", f"sqlite:///{tmp_path.as_posix()}/personal.db")
    monkeypatch.setattr(config, "PERSONAL_MODEL_DIR", tmp_path / "private-models")
    monkeypatch.setattr(config, "SCENARIO_DATABASE_URL", f"sqlite:///{tmp_path.as_posix()}/scenario.db")
    monkeypatch.setattr(config, "GMAIL_CLIENT_ID", "synthetic-client-id")
    monkeypatch.setattr(config, "GMAIL_CLIENT_SECRET", "synthetic-client-secret")
    monkeypatch.setattr(config, "GMAIL_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr(config, "GMAIL_REDIRECT_URI", "http://127.0.0.1:8000/api/gmail/callback")
    monkeypatch.setattr(config, "GMAIL_FRONTEND_URL", "http://127.0.0.1:5173")
    google = Google()
    transport = httpx.MockTransport(google.respond)
    original_client = httpx.Client
    monkeypatch.setattr(
        gmail_service, "HTTPClient", lambda **kwargs: original_client(transport=transport, **kwargs)
    )

    monkeypatch.setattr(
        gmail_service,
        "OAuth2Client",
        lambda *args, **kwargs: OAuth2Client(*args, transport=transport, **kwargs),
    )
    with TestClient(
        main.app,
        base_url="http://127.0.0.1:8000",
        client=("127.0.0.1", 50000),
        headers={"Origin": config.GMAIL_FRONTEND_URL},
    ) as client:
        yield client, google, tmp_path
    engine.dispose()


def authorize(client):
    response = client.post("/api/gmail/connect")
    assert response.status_code == 200, response.text
    query = parse_qs(urlsplit(response.json()["authorization_url"]).query)
    assert query["scope"] == [config.GMAIL_SCOPE]
    assert query["response_type"] == ["code"]
    assert query["access_type"] == ["offline"]
    assert query["code_challenge_method"] == ["S256"]
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "client_secret" not in response.text
    state = query["state"][0]
    verifier = main.app.state.gmail.states[state]["verifier"]
    expected = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    assert query["code_challenge"] == [expected]
    return client.get(
        "/api/gmail/callback", params={"state": state, "code": "synthetic-code"}, follow_redirects=False
    ), state


def register(client, **changes):
    data = {
        "name": "My checking",
        "account_type": "checking",
        "last_four": "1234",
        "opening_balance": "10.00",
        "balance_date": "2026-10-09",
        **changes,
    }
    response = client.post("/api/gmail/accounts", json=data)
    assert response.status_code == 201, response.text
    return response.json()[-1]["id"]


def personal(client):
    assert client.post("/api/workspace", json={"workspace": "personal"}).status_code == 200


def confirm_payload(item, account_id, **changes):
    return {
        "date": item["date"],
        "merchant": item["merchant"],
        "description": item["merchant"],
        "amount": item["amount"],
        "kind": "income"
        if item["event_type"] == "income"
        else "refund"
        if item["event_type"] == "refund"
        else "expense",
        "category": item["category"],
        "account_id": account_id,
        "posted_confirmed": True,
        **changes,
    }


def authenticated_email(identifier, amount="15.00", merchant="Chick-fil-A", body=None):
    message = email(
        identifier, body or f"Posted purchase of ${amount} at {merchant} on 2026-10-09. Card ending in 1234."
    )
    message["payload"]["headers"] = [
        {"name": "Received", "value": "from bank.invalid by mx.google.com with ESMTPS; Fri, 9 Oct 2026"},
        {
            "name": "Authentication-Results",
            "value": "mx.google.com; spf=pass smtp.mailfrom=alerts@synthetic-bank.edu; dkim=pass header.d=synthetic-bank.edu; dmarc=pass header.from=synthetic-bank.edu",
        },
        {"name": "From", "value": "Financial Alerts <alerts@synthetic-bank.edu>"},
        {"name": "Subject", "value": "Posted financial alert"},
    ]
    return message


def test_smartapprove_confirmed_payroll_purchase_and_exact_domain_rule(gmail):
    client, google, _ = gmail
    account = register(client)
    personal(client)
    trusted_rule(
        client,
        account,
        sender="synthetic-bank.edu",
        match_type="domain",
        enabled=True,
        transaction_limit="500.00",
        daily_limit="500.00",
    )
    authorize(client)
    google.messages = {
        "payroll": authenticated_email(
            "payroll",
            body="Confirmed posted direct deposit of $400.00 from Campus job payroll on 2026-10-09. Checking account ending in 1234.",
        ),
        "meal": authenticated_email("meal"),
    }
    assert client.post("/api/gmail/sync").json()["auto_approved"] == 2
    data = client.get("/api/dashboard").json()
    assert (data["balance"], data["income"], data["expenses"]) == (395, 400, 15)
    assert client.get("/api/gmail/accounts").json()[0]["estimated"] is True
    question = {"question": "When was my last confirmed paycheck?"}
    assert client.post("/api/assistant", json=question).json()["evidence"]["last_paycheck"]["amount"] == 400
    paycheck = next(t for t in client.get("/api/transactions").json() if t["kind"] == "income")
    assert client.post(f"/api/smartapprove/transactions/{paycheck['id']}/reverse").status_code == 200
    data = client.get("/api/dashboard").json()
    assert (data["balance"], data["income"]) == (-5, 0)
    assert client.post("/api/assistant", json=question).json()["evidence"]["last_paycheck"] is None


def test_smartapprove_event_restriction_account_restriction_and_daily_exact_cap(gmail):
    client, google, _ = gmail
    account = register(client)
    personal(client)
    rule = trusted_rule(client, account, enabled=True, daily_limit="25.00", events=["purchase"])
    authorize(client)
    google.messages = {
        "p1": authenticated_email("p1"),
        "p2": authenticated_email("p2", amount="10.00", merchant="Kroger grocery"),
        "p3": authenticated_email("p3", amount="0.01", merchant="Target shopping"),
        "income": authenticated_email(
            "income",
            body="Confirmed posted direct deposit of $20.00 from Campus job payroll on 2026-10-09. Account ending in 1234.",
        ),
    }
    assert client.post("/api/gmail/sync").json()["auto_approved"] == 2
    assert client.get("/api/dashboard").json()["income"] == 0
    other = register(client, name="Savings", account_type="savings", last_four="9999")
    assert (
        client.put(
            f"/api/smartapprove/rules/{rule['id']}",
            json={**rule, "account_id": other, "daily_limit": "500.00"},
        ).status_code
        == 200
    )
    google.messages["account-mismatch"] = authenticated_email("account-mismatch", amount="11.00")
    assert client.post("/api/gmail/sync").json()["auto_approved"] == 0
    row = client.get("/api/gmail/items").json()[0]
    assert any("account" in s.lower() for s in row["reasons"])


def trusted_rule(client, account, **changes):
    data = {
        "sender": "alerts@synthetic-bank.edu",
        "institution": "Synthetic Bank",
        "account_id": account,
        "events": ["purchase", "income", "refund", "subscription"],
        "transaction_limit": "100.00",
        "daily_limit": "500.00",
        **changes,
    }
    r = client.post("/api/smartapprove/rules", json=data)
    assert r.status_code == 201, r.text
    return r.json()


def test_smartapprove_default_off_crud_audit_and_exact_domains(gmail):
    client, google, _ = gmail
    account = register(client)
    personal(client)
    rule = trusted_rule(client, account)
    assert rule["enabled"] is False
    assert authorize(client)[0].status_code == 303
    google.messages = {"auth1": authenticated_email("auth1")}
    assert client.post("/api/gmail/sync").json()["auto_approved"] == 0
    assert client.get("/api/dashboard").json()["balance"] == 10
    assert client.get("/api/smartapprove/summary?workspace=active").json()["pending"] == 1
    assert client.post("/api/workspace", json={"workspace": "demo"}).status_code == 200
    assert client.get("/api/smartapprove/summary?workspace=active").json()["pending"] == 0
    assert client.get("/api/smartapprove/summary").json()["pending"] == 1
    personal(client)
    from backend.app.smartapprove import authentication

    forged = authenticated_email("forged")
    forged["payload"]["headers"][0]["value"] = (
        "from attacker.edu by mx.google.com.attacker.edu; Fri, 9 Oct 2026"
    )
    assert authentication(forged)["aligned"] is False
    missing_delivery = authenticated_email("missing-delivery")
    missing_delivery["labelIds"] = []
    assert authentication(missing_delivery)["aligned"] is False
    synthetic = authenticated_email(
        "explicit-test",
        body="Synthetic posted purchase of $15.00 at Chick-fil-A on 2026-10-09. Card ending in 1234.",
    )
    parsed = parse_financial_email(synthetic, main.app.state.personal_classifier)
    assert any("Synthetic or test email" in reason for reason in parsed["reasons"])
    assert (
        client.put(
            f"/api/smartapprove/rules/{rule['id']}", json={**rule, "enabled": True, "suspended": True}
        ).status_code
        == 200
    )
    assert client.get("/api/smartapprove/summary").json()["active_senders"] == 0
    assert client.delete(f"/api/smartapprove/rules/{rule['id']}").status_code == 200
    assert client.get("/api/smartapprove/rules").json() == []
    assert {a["action"] for a in client.get("/api/smartapprove/summary").json()["history"]} >= {
        "rule-created",
        "rule-updated",
        "rule-removed",
    }
    assert (
        client.post(
            "/api/smartapprove/rules", json={**rule, "sender": "*.synthetic-bank.edu", "match_type": "domain"}
        ).status_code
        == 422
    )


@pytest.mark.parametrize(
    "case",
    [
        "no-auth",
        "spf-fail",
        "dkim-fail",
        "dmarc-fail",
        "misaligned",
        "forged-boundary",
        "duplicate-auth",
        "duplicate-from",
        "arc",
        "synthetic",
        "subdomain",
        "pending",
        "order",
        "paystub",
        "transfer",
        "wrong-account",
        "limit",
        "future",
        "uncertain-merchant",
    ],
)
def test_smartapprove_fail_closed(gmail, case):
    client, google, _ = gmail
    account = register(client)
    personal(client)
    trusted_rule(client, account, enabled=True, transaction_limit="20.00")
    authorize(client)
    msg = authenticated_email("case1")
    headers = msg["payload"]["headers"]
    if case == "no-auth":
        headers.pop(1)
    elif case in {"spf-fail", "dkim-fail", "dmarc-fail"}:
        headers[1]["value"] = headers[1]["value"].replace(
            case.split("-")[0] + "=pass", case.split("-")[0] + "=fail"
        )
    elif case == "misaligned":
        headers[1]["value"] = headers[1]["value"].replace(
            "header.d=synthetic-bank.edu", "header.d=attacker.edu"
        )
    elif case == "forged-boundary":
        headers.pop(0)
    elif case == "duplicate-auth":
        headers.insert(2, dict(headers[1]))
    elif case == "duplicate-from":
        headers.append(dict(headers[2]))
    elif case == "arc":
        headers.append({"name": "ARC-Authentication-Results", "value": "i=1; untrusted; spf=pass"})
    elif case in {"synthetic", "subdomain"}:
        replacement = "bank.example.test" if case == "synthetic" else "sub.synthetic-bank.edu"
        for h in headers:
            h["value"] = h["value"].replace("synthetic-bank.edu", replacement)
    elif case in {"pending", "order", "paystub", "transfer"}:
        msg = authenticated_email(
            "case1",
            body=f"Posted purchase of $15.00 at Chick-fil-A on 2026-10-09. Card ending in 1234. {dict(pending='Pending authorization', order='Order confirmation', paystub='Pay stub', transfer='Account transfer')[case]}.",
        )
    elif case == "wrong-account":
        msg = authenticated_email(
            "case1", body="Posted purchase of $15.00 at Chick-fil-A on 2026-10-09. Card ending in 9999."
        )
    elif case == "limit":
        msg = authenticated_email("case1", amount="20.01")
    elif case == "future":
        msg = authenticated_email(
            "case1", body="Posted purchase of $15.00 at Chick-fil-A on 2026-10-10. Card ending in 1234."
        )
    elif case == "uncertain-merchant":
        msg = authenticated_email("case1", merchant="Unidentified QZX merchant")
    google.messages = {"case1": msg}
    assert client.post("/api/gmail/sync").json()["auto_approved"] == 0
    assert client.get("/api/dashboard").json()["balance"] == 10
    assert client.get("/api/gmail/items").json()[0]["status"] == "review"


def test_smartapprove_daily_deduplication_correction_reversal(gmail):
    client, google, _ = gmail
    account = register(client, opening_balance="100.00")
    personal(client)
    trusted_rule(client, account, enabled=True, daily_limit="25.00")
    authorize(client)
    google.messages = {
        "p1": authenticated_email("p1"),
        "receipt": authenticated_email("receipt"),
        "p2": authenticated_email("p2", merchant="Kroger grocery"),
    }
    result = client.post("/api/gmail/sync").json()
    assert result["auto_approved"] == 1
    assert len(client.get("/api/transactions").json()) == 1
    assert client.post("/api/gmail/sync").json()["already_seen"] == 3
    tx = client.get("/api/transactions").json()[0]
    assert client.delete(f"/api/transactions/{tx['id']}").status_code == 409
    payload = {
        "description": tx["description"],
        "merchant": tx["merchant"],
        "date": tx["date"],
        "account_id": account,
        "amount": "12.00",
        "category": "food",
    }
    assert client.put(f"/api/transactions/{tx['id']}", json=payload).status_code == 200
    assert client.get("/api/dashboard").json()["balance"] == 88
    assert client.post(f"/api/smartapprove/transactions/{tx['id']}/reverse").status_code == 200
    assert client.post(f"/api/smartapprove/transactions/{tx['id']}/reverse").status_code == 409
    data = client.get("/api/dashboard").json()
    assert data["balance"] == 100 and data["expenses"] == 0
    assert client.put(f"/api/transactions/{tx['id']}", json=payload).status_code == 409
    adjustment = next(
        t for t in client.get("/api/transactions").json() if t["source"] == "smartapprove-adjustment"
    )
    assert client.delete(f"/api/transactions/{adjustment['id']}").status_code == 409
    assert client.put(f"/api/transactions/{adjustment['id']}", json=payload).status_code == 409
    google.messages["after-reversal"] = authenticated_email("after-reversal")
    assert client.post("/api/gmail/sync").json()["auto_approved"] == 0
    assert client.get("/api/dashboard").json()["balance"] == 100
    assert {a["action"] for a in client.get("/api/smartapprove/summary").json()["history"]} >= {
        "corrected",
        "reversed",
        "auto-approved",
    }


def test_gmail_auto_purchase_to_circle_and_manually_matched_reimbursement(gmail):
    from uuid import uuid4

    client, google, _ = gmail
    account = register(client, opening_balance="100.00")
    personal(client)
    trusted_rule(client, account, enabled=True)
    authorize(client)
    google.messages = {"dinner": authenticated_email("dinner", amount="40.00")}
    assert client.post("/api/gmail/sync").json()["auto_approved"] == 1
    tx = client.get("/api/transactions").json()[0]
    c = client.post(
        "/api/circles", json={"name": "Roommates", "kind": "roommates", "participants": ["Jordan"]}
    ).json()
    expense = client.post(
        f"/api/circles/{c['id']}/expenses",
        json={
            "title": "Shared dinner",
            "date": tx["date"],
            "amount": "40.00",
            "payer_id": c["members"][0]["id"],
            "transaction_id": tx["id"],
            "shares": {str(m["id"]): "0" for m in c["members"]},
        },
    ).json()["expenses"][0]
    assert client.get("/api/dashboard").json()["expenses"] == 20
    assert client.get("/api/dashboard").json()["balance"] == 60
    google.messages["repay"] = email(
        "repay", "Deposit received of $20.00 from Jordan on 2026-10-09. Account ending in 1234."
    )
    client.post("/api/gmail/sync")
    item = next(i for i in client.get("/api/gmail/items").json() if i["status"] == "review")
    incoming = client.post(
        f"/api/gmail/items/{item['id']}/confirm", json=confirm_payload(item, account)
    ).json()["transaction"]
    assert client.get("/api/dashboard").json()["income"] == 20
    assert (
        client.post(
            f"/api/circles/expenses/{expense['id']}/settlements",
            json={
                "member_id": c["members"][1]["id"],
                "amount": "20.00",
                "date": tx["date"],
                "transaction_id": incoming["id"],
                "request_key": str(uuid4()),
                "confirmed": True,
            },
        ).status_code
        == 201
    )
    data = client.get("/api/dashboard").json()
    assert (data["balance"], data["expenses"], data["income"]) == (80, 20, 0)
    assert len(client.get("/api/transactions").json()) == 2
    assert client.get("/api/circles").json()[0]["receivable_cents"] == 0


def test_controlled_scenario_preserves_real_demo_gmail_and_private_data(gmail):
    client, google, _ = gmail
    original = client.get("/api/dashboard").json()["balance"]
    account = register(client)
    authorize(client)
    assert client.post("/api/upgrade-demo/start").status_code == 200
    assert client.get("/api/dashboard").json()["balance"] == 100
    google_calls = len(google.requests)
    assert client.post("/api/gmail/sync").status_code == 403
    assert client.get("/api/gmail/status").status_code == 403
    assert client.post("/api/upgrade-demo/alert").json()["auto_approved"] is True
    assert client.get("/api/dashboard").json()["balance"] == 60
    assert client.post("/api/upgrade-demo/alert").status_code == 409
    assert len(google.requests) == google_calls
    assert client.post("/api/workspace", json={"workspace": "demo"}).status_code == 200
    assert client.get("/api/dashboard").json()["balance"] == original
    personal(client)
    assert client.get("/api/gmail/status").json()["connected"] is True
    assert client.get("/api/gmail/accounts").json()[0]["id"] == account
    assert client.get("/api/dashboard").json()["balance"] == 10


def test_no_reads_before_authorization_and_encrypted_backend_only_tokens(gmail):
    client, google, root = gmail
    assert client.post("/api/gmail/sync").status_code == 401
    assert google.requests == []
    response, state = authorize(client)
    assert response.status_code == 303
    assert response.headers["location"] == "http://127.0.0.1:5173/?gmail=connected#settings"
    assert "synthetic-access" not in response.text
    encrypted = (root / "gmail/credentials.enc").read_bytes()
    assert b"synthetic-access" not in encrypted and b"synthetic-refresh" not in encrypted
    status = client.get("/api/gmail/status")
    assert status.json()["email"] == "synthetic-user@example.test"
    assert "token" not in status.text.replace('"tokens_present"', "")
    assert (
        client.get("/api/gmail/callback", params={"state": state, "code": "synthetic-code"}).status_code
        == 400
    )
    assert STATE_COOKIE not in client.cookies


def test_confirmed_paycheck_purchase_balances_forecast_budget_and_demo_isolation(gmail):
    client, google, _ = gmail
    original = client.get("/api/dashboard").json()
    account = register(client)
    personal(client)
    assert client.get("/api/dashboard").json()["balance"] == 10
    assert client.get("/api/transactions").json() == []
    assert client.put("/api/budgets", json={"category": "food", "limit": 100}).status_code == 200
    assert authorize(client)[0].status_code == 303
    google.messages = {
        "income1": email(
            "income1",
            "Confirmed direct deposit of $400.00 from Campus job payroll on 2026-10-09. Checking account ending in 1234.",
        ),
        "purchase1": email(
            "purchase1", "Your card ending in 1234 was charged $15.00 at Chick-fil-A on 2026-10-09."
        ),
    }
    assert client.post("/api/gmail/sync").json()["queued"] == 2
    assert client.get("/api/dashboard").json()["balance"] == 10
    items = client.get("/api/gmail/items").json()
    income = next(i for i in items if i["event_type"] == "income")
    purchase = next(i for i in items if i["event_type"] == "purchase")
    assert income["amount"] == 400 and purchase["amount"] == 15
    assert income["account_id"] == purchase["account_id"] == account
    assert purchase["category"] == "food"
    assert (
        client.post(
            f"/api/gmail/items/{income['id']}/confirm", json=confirm_payload(income, account)
        ).status_code
        == 200
    )
    assert client.get("/api/dashboard").json()["balance"] == 410
    assert (
        client.post(
            f"/api/gmail/items/{purchase['id']}/confirm", json=confirm_payload(purchase, account)
        ).status_code
        == 200
    )
    assert client.get("/api/dashboard").json()["balance"] == 395
    assert client.get("/api/forecast").json()["current_balance"] == 395
    assert client.get("/api/gmail/accounts").json()[0]["balance"] == 395
    assert client.get("/api/budgets").json()[0]["spent"] == 15
    assert client.post("/api/demo/reset").status_code == 409
    assert client.post("/api/demo/import-sample").status_code == 409
    assert client.post("/api/gmail/sync").json()["queued"] == 0
    assert len(client.get("/api/transactions").json()) == 2
    assert client.post("/api/workspace", json={"workspace": "demo"}).status_code == 200
    assert client.get("/api/dashboard").json()["balance"] == original["balance"]
    assert client.get("/api/dashboard").json()["expenses"] == original["expenses"]


def test_ambiguous_bill_requires_posted_confirmation_and_manual_fields(gmail):
    client, google, _ = gmail
    account = register(client)
    personal(client)
    authorize(client)
    google.messages = {
        "bill1": email(
            "bill1", "Upcoming utility bill of $30.00 from Electric Company. Your current balance is $50.00."
        )
    }
    assert client.post("/api/gmail/sync").status_code == 200
    item = client.get("/api/gmail/items").json()[0]
    assert item["event_type"] == "bill" and item["amount"] is None and item["account_id"] is None
    assert len(item["reasons"]) >= 2
    assert (
        client.post(
            f"/api/gmail/items/{item['id']}/confirm",
            json=confirm_payload(item, account, amount=30, posted_confirmed=False),
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"/api/gmail/items/{item['id']}/confirm",
            json=confirm_payload(item, account, amount=30, date="2026-10-10"),
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"/api/gmail/items/{item['id']}/confirm",
            json=confirm_payload(item, account, amount=30, notification_text="Raw email body"),
        ).status_code
        == 422
    )
    assert client.get("/api/dashboard").json()["balance"] == 10
    assert client.post(f"/api/gmail/items/{item['id']}/dismiss").status_code == 200
    assert client.post(f"/api/gmail/items/{item['id']}/dismiss").status_code == 409
    assert client.post("/api/gmail/sync").json()["queued"] == 0


def test_message_ids_and_cross_message_transaction_duplicates(gmail):
    client, google, _ = gmail
    account = register(client)
    personal(client)
    authorize(client)
    body = "Purchase charged $15.00 at Chick-fil-A. Card ending in 1234."
    google.messages = {"one": email("one", body), "two": email("two", body)}
    client.post("/api/gmail/sync")
    items = client.get("/api/gmail/items").json()
    first = client.post(f"/api/gmail/items/{items[0]['id']}/confirm", json=confirm_payload(items[0], account))
    assert first.json()["status"] == "confirmed"
    assert (
        client.post(
            f"/api/gmail/items/{items[1]['id']}/confirm", json=confirm_payload(items[1], account)
        ).json()["status"]
        == "duplicate"
    )
    transaction = first.json()["transaction"]["id"]
    assert client.delete(f"/api/transactions/{transaction}").status_code == 204
    assert client.post("/api/gmail/sync").json()["queued"] == 0
    assert client.get("/api/dashboard").json()["balance"] == 10


@pytest.mark.parametrize("failure", ["wrong-state", "wrong-browser", "expired", "missing-code"])
def test_oauth_state_is_single_use_browser_bound_and_expiring(gmail, failure):
    client, google, _ = gmail
    url = client.post("/api/gmail/connect").json()["authorization_url"]
    state = parse_qs(urlsplit(url).query)["state"][0]
    params = {"state": state, "code": "synthetic-code"}
    if failure == "wrong-state":
        params["state"] = "wrong"
    elif failure == "wrong-browser":
        client.cookies.clear()
    elif failure == "expired":
        main.app.state.gmail.states[state]["expires"] = time.time() - 1
    else:
        del params["code"]
    assert client.get("/api/gmail/callback", params=params).status_code == 400
    assert google.requests == []


def test_denied_permission_and_wrong_scope_leave_no_tokens(gmail):
    client, google, root = gmail
    url = client.post("/api/gmail/connect").json()["authorization_url"]
    state = parse_qs(urlsplit(url).query)["state"][0]
    denied = client.get(
        "/api/gmail/callback", params={"state": state, "error": "access_denied"}, follow_redirects=False
    )
    assert denied.status_code == 303 and "gmail=denied" in denied.headers["location"]
    assert google.requests == []
    google.scope = "openid"
    assert authorize(client)[0].status_code == 400
    assert not (root / "gmail/credentials.enc").exists()


def test_refresh_disconnect_and_google_revoke_failure(gmail):
    client, google, root = gmail
    authorize(client)
    service = main.app.state.gmail
    stored = service.vault.load()
    stored["token"]["expires_at"] = time.time() - 1
    service.vault.save(stored)
    assert client.post("/api/gmail/sync").status_code == 200
    refreshes = [
        r for r in google.requests if r.url.path.endswith("/token") and b"refresh_token" in r.content
    ]
    assert refreshes
    google.revoke_ok = False
    result = client.post("/api/gmail/disconnect")
    assert result.json()["google_revoked"] is False
    assert not (root / "gmail/credentials.enc").exists()
    assert client.post("/api/gmail/sync").status_code == 401


def test_revoked_refresh_requires_reconnection_without_changing_balances(gmail):
    client, google, _ = gmail
    authorize(client)
    stored = main.app.state.gmail.vault.load()
    stored["token"]["expires_at"] = 0
    main.app.state.gmail.vault.save(stored)
    google.refresh_ok = False
    assert client.post("/api/gmail/sync").status_code == 401
    assert client.get("/api/gmail/items").json() == []


def test_disconnect_can_remove_unreadable_credentials(gmail, monkeypatch):
    client, _, root = gmail
    authorize(client)
    monkeypatch.setattr(config, "GMAIL_TOKEN_ENCRYPTION_KEY", "")
    main.app.state.gmail.vault = None
    assert client.get("/api/gmail/status").json()["tokens_present"]
    assert client.post("/api/gmail/disconnect").json()["google_revoked"] is False
    assert not (root / "gmail/credentials.enc").exists()


def test_personal_write_origin_and_non_loopback_clients_are_rejected(gmail):
    client, google, _ = gmail
    assert client.post("/api/gmail/connect", headers={"Origin": "https://evil.example"}).status_code == 403
    assert (
        client.post("/api/workspace", headers={"Origin": ""}, json={"workspace": "personal"}).status_code
        == 403
    )
    assert client.get("/api/gmail/status", headers={"Host": "evil.example"}).status_code == 403
    assert client.get("/api/gmail/items", headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
    remote = TestClient(main.app, base_url="http://127.0.0.1:8000", client=("203.0.113.20", 50000))
    assert remote.get("/api/gmail/status").status_code == 403
    remote.close()
    assert google.requests == []


def test_private_corrections_and_deletion_leave_demo_model_untouched(gmail):
    client, _, _ = gmail
    demo_model = main.app.state.classifier.pipeline
    account = register(client)
    personal(client)
    response = client.post(
        "/api/transactions",
        json={
            "date": "2026-10-09",
            "description": "Private synthetic cafe new merchant",
            "amount": 5,
            "kind": "expense",
            "category": "food",
            "account_id": account,
        },
    )
    assert response.status_code == 201
    assert client.post("/api/ml/retrain").status_code == 200
    assert main.app.state.personal_classifier is not main.app.state.classifier
    assert main.app.state.classifier.pipeline is demo_model
    assert client.delete("/api/data").status_code == 204
    assert main.app.state.classifier.pipeline is demo_model


def test_account_constraints_dates_credit_income_and_scoped_dedupe(gmail):
    client, google, _ = gmail
    checking = register(client)
    savings = register(client, name="Savings", last_four="5678", account_type="savings", opening_balance=0)
    credit = register(client, name="Credit", last_four="9999", account_type="credit", opening_balance=-20)
    personal(client)
    body = {
        "date": "2026-10-09",
        "description": "Chick-fil-A",
        "merchant": "Chick-fil-A",
        "amount": 15,
        "kind": "expense",
        "category": "food",
    }
    assert client.post("/api/transactions", json={**body, "account_id": checking}).status_code == 201
    assert client.post("/api/transactions", json={**body, "account_id": savings}).status_code == 201
    assert client.post("/api/transactions", json={**body, "account_id": savings}).status_code == 409
    assert client.post("/api/transactions", json={**body, "account_id": 123}).status_code == 422
    assert (
        client.post(
            "/api/transactions", json={**body, "account_id": checking, "date": "2026-10-08"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/transactions", json={**body, "account_id": credit, "kind": "income", "category": "income"}
        ).status_code
        == 422
    )
    authorize(client)
    google.messages = {
        "deposit": email(
            "deposit", "Posted payroll deposit $400.00 from Campus job payroll. Card ending in 9999."
        )
    }
    client.post("/api/gmail/sync")
    item = client.get("/api/gmail/items").json()[0]
    assert item["account_id"] is None
    assert (
        client.post(f"/api/gmail/items/{item['id']}/confirm", json=confirm_payload(item, credit)).status_code
        == 422
    )


def test_private_export_delete_retains_empty_workspace_and_disconnects(gmail):
    client, _, root = gmail
    register(client)
    personal(client)
    authorize(client)
    exported = client.get("/api/export").json()
    assert exported["synthetic"] is False
    assert "synthetic-access" not in json.dumps(exported)
    assert client.delete("/api/data").status_code == 204
    assert client.get("/api/dashboard").json()["balance"] == 0
    assert client.get("/api/profile").json() is None
    assert client.get("/api/gmail/accounts").json() == []
    assert client.get("/api/export").json()["synthetic"] is False
    assert not (root / "gmail/credentials.enc").exists()
    main.app.state.personal_engine.dispose()
    main.app.state.personal_engine = None
    assert client.get("/api/profile").json() is None
    assert client.get("/api/transactions").json() == []


def test_bounded_sync_persists_pagination_and_handles_api_errors(gmail):
    client, google, _ = gmail
    authorize(client)
    google.next_page = "synthetic-next-page"
    result = client.post("/api/gmail/sync")
    assert result.json()["more_available"]
    assert len([r for r in google.requests if r.url.path.endswith("/messages")]) == 5
    assert main.app.state.gmail.vault.load()["sync_cursor"] == google.next_page
    google.api_status = 429
    assert client.post("/api/gmail/sync").status_code == 503
    assert client.get("/api/gmail/items").json() == []


@pytest.mark.parametrize(
    "body,event,amount",
    [
        ("Your card ending in 1234 was charged $15.00 at Chick-fil-A.", "purchase", 1500),
        ("Confirmed paycheck deposit $400.00 from Campus job payroll.", "income", 40000),
        ("Refund posted $5.00 from Target.", "refund", 500),
        ("Subscription charged $12.99 at Netflix.", "subscription", 1299),
        ("Upcoming bill due $40.00 from Utility Company.", "bill", 4000),
        ("Purchase $15.00 at Kroger. Available balance $500.00.", "purchase", None),
        ("Purchase charged $1.234 at Kroger.", "purchase", None),
        ("Purchase charged CAD $15.00 at Kroger.", "purchase", None),
    ],
)
def test_synthetic_financial_email_detection(ml, body, event, amount):
    result = parse_financial_email(email("synthetic", body), ml)
    assert result["event_type"] == event and result["amount_cents"] == amount
    assert "notification_text" not in result


def test_html_attachments_marketing_spam_and_ambiguous_suffixes(ml):
    html = '<script>Purchase $9000 at Evil</script><p>Your card ending in 1234 was charged $15.00 at Chick-fil-A.</p><img src="https://tracker.example/pixel">'
    message = email("html", html, mime="text/html")
    message["payload"]["parts"] = [
        {
            "filename": "secret.txt",
            "mimeType": "text/plain",
            "body": {"data": base64.urlsafe_b64encode(b"Purchase $800 at Evil").decode()},
        }
    ]
    parsed = parse_financial_email(message, ml)
    assert parsed["amount_cents"] == 1500 and parsed["last_four"] == "1234"
    assert (
        parse_financial_email(email("spam", "Purchase charged $15 at Chick-fil-A.", labelIds=["SPAM"]), ml)
        is None
    )
    assert parse_financial_email(email("promo", "Subscription coupon discount $15 at Netflix."), ml) is None
    mixed = parse_financial_email(
        email("mixed", "Purchase charged $15 at Kroger. Cards ending in 1234 and ending in 5678."), ml
    )
    assert mixed["last_four"] is None and any("Multiple card" in x for x in mixed["reasons"])


def test_token_vault_roundtrip_and_wrong_key_detection(tmp_path):
    vault = TokenVault(tmp_path, Fernet.generate_key().decode())
    vault.save({"token": {"access_token": "synthetic-private-token"}})
    assert vault.load()["token"]["access_token"] == "synthetic-private-token"
    wrong = TokenVault(tmp_path, Fernet.generate_key().decode())
    with pytest.raises(Exception, match="cannot be decrypted"):
        wrong.load()


def test_dashboard_synthetic_approvals_balance_and_private_isolation(gmail):
    client, google, _ = gmail
    register(client)
    client.post('/api/workspace', json={'workspace':'personal'})
    before = client.get('/api/dashboard').json()['balance']
    assert client.post('/api/upgrade-demo/start', json={'starting_balance':'10.00'}).status_code == 200
    assert client.get('/api/dashboard').json()['balance'] == 10
    for event, expected in [('paycheck',410),('purchase',395)]:
        r=client.post('/api/upgrade-demo/financial-alert',json={'event':event})
        assert r.status_code == 200, r.text
        item=r.json()
        assert item['reasons']  # Synthetic sender cannot silently auto-approve.
        assert len(client.get('/api/approvals').json()['items']) == 1
        payload=confirm_payload(item,1)
        response=client.post(f"/api/approvals/{item['id']}/confirm",json=payload)
        assert response.status_code == 200, response.text
        assert client.get('/api/dashboard').json()['balance'] == expected
        assert client.post(f"/api/approvals/{item['id']}/confirm",json=payload).status_code == 409
        assert client.post('/api/upgrade-demo/financial-alert',json={'event':event}).json()['status'] == 'confirmed'
    assert client.get('/api/approvals').json()['items'] == []
    reply=client.post('/api/assistant',json={'question':'When was my last confirmed paycheck?'}).json()
    assert reply['evidence']['last_paycheck']['amount'] == 400
    assert len(google.requests) == 0
    client.post('/api/workspace',json={'workspace':'personal'})
    assert client.get('/api/dashboard').json()['balance'] == before
    assert client.get('/api/approvals').json()['items'] == []


def test_linked_debit_card_matching_no_duplicate_balance(gmail):
    client, _, _ = gmail
    account=register(client)
    client.post('/api/workspace',json={'workspace':'personal'})
    r=client.post(f'/api/accounts/{account}/debit-cards',json={'name':'Everyday debit','last_four':'4321'})
    assert r.status_code == 201, r.text
    assert r.json()[0]['balance'] == 10
    from backend.app.gmail_routes import match_account
    from backend.app.database import personal_engine
    from sqlalchemy.orm import Session
    with Session(personal_engine(main.app)) as db:
        assert match_account(db,{'last_four':'4321','event_type':'purchase','reasons':[]}) == account
    assert client.post(f'/api/accounts/{account}/debit-cards',json={'name':'Duplicate','last_four':'4321'}).status_code == 409
    assert client.post('/api/gmail/accounts',json={'name':'Other','account_type':'checking','last_four':'4321','opening_balance':0,'balance_date':'2026-10-09'}).status_code == 409


def test_atomic_transfers_card_payment_and_reconciliation(gmail):
    client, _, _ = gmail
    checking=register(client,opening_balance=100)
    saving=register(client,name='Savings',last_four='5678',account_type='savings',opening_balance=20)
    credit=register(client,name='Credit',last_four='9999',account_type='credit',opening_balance=-50)
    client.post('/api/workspace',json={'workspace':'personal'})
    assert client.get('/api/dashboard').json()['balance'] == 120
    body={'from_account':checking,'to_account':saving,'amount':'20.00','date':'2026-10-09','request_key':'transfer-savings-1'}
    assert client.post('/api/accounts/transfers',json=body).status_code == 200
    assert client.post('/api/accounts/transfers',json=body).status_code == 200
    assert client.post('/api/accounts/transfers',json={**body,'amount':30}).status_code == 409
    data=client.get('/api/dashboard').json()
    assert (data['balance'],data['income'],data['expenses'],data['cash_expenses']) == (120,0,0,0)
    r=client.post('/api/accounts/transfers',json={**body,'to_account':credit,'amount':50,'request_key':'credit-payment-1'})
    assert r.status_code == 200, r.text
    assert next(a for a in r.json() if a['id']==credit)['outstanding'] == 0
    assert client.get('/api/dashboard').json()['balance'] == 70
    assert client.get('/api/dashboard').json()['expenses'] == 0
    assert client.post('/api/accounts/transfers',json={**body,'from_account':credit,'request_key':'credit-funded-1'}).status_code == 422
    assert client.post(f'/api/accounts/{checking}/reconcile',json={'observed_balance':35}).status_code == 422
    assert client.post(f'/api/accounts/{checking}/reconcile',json={'observed_balance':35,'confirmed':True}).status_code == 200
    data=client.get('/api/dashboard').json()
    assert (data['balance'],data['income'],data['expenses']) == (75,0,0)
    rows=client.get('/api/transactions').json()
    assert len(rows)==5
    for t in rows:
        assert client.delete(f"/api/transactions/{t['id']}").status_code == 409
    assert client.post(f'/api/accounts/{credit}/debit-cards',json={'name':'Wrong','last_four':'2222'}).status_code == 422


def test_account_management_does_not_edit_demo_or_real_scenario_mail(gmail):
    client, _, _ = gmail
    assert client.get('/api/accounts').status_code == 409
    client.post('/api/upgrade-demo/start')
    assert client.post('/api/gmail/sync').status_code == 403
    assert client.get('/api/approvals').json()['items'] == []
