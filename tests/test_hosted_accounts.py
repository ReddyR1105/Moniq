"""Synthetic identities and mocked Gmail only. No local-owner database or inbox."""
import base64
import os
import secrets
import time
import uuid
from dataclasses import replace
from urllib.parse import parse_qs, urlsplit

import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from backend.app import config, main
from backend.app.hosted_gmail import DatabaseVault, HostedGmailManager
from backend.app.hosted_settings import HostedSettings
from backend.app.identity import AUTH_COOKIE, IdentityStore, TLSMailer, digest
from backend.app.identity_models import AuthSession, GmailCredential, OAuthAttempt, User

ORIGIN = "https://moniq.test"
ALICE = "alice@moniq.example.test"
BOB = "bob@moniq.example.test"
PASSWORD = "synthetic student password 123"


class Mailbox:
    def __init__(self):
        self.messages = []

    def send(self, email, purpose, token):
        self.messages.append((email, purpose, token))


@pytest.fixture
def hosted_app(tmp_path, monkeypatch, ml):
    settings = HostedSettings(enabled=True, private_enabled=True, origin=ORIGIN,
                              session_key=secrets.token_urlsafe(48), allowed_emails=(ALICE, BOB),
                              gmail_enabled=True, gmail_client_id="synthetic-client.apps.googleusercontent.com",
                              gmail_client_secret="synthetic-test-credential", gmail_key=Fernet.generate_key().decode())
    postgres = os.getenv("MONIQ_TEST_POSTGRES_URL")
    admin = None
    database_name = "moniq_test_" + uuid.uuid4().hex
    if postgres:
        admin = create_engine(postgres, isolation_level="AUTOCOMMIT", hide_parameters=True)
        if admin.url.host not in {"localhost", "127.0.0.1"} or admin.url.database != "postgres":
            raise ValueError("Integration tests require a disposable local PostgreSQL cluster, never a hosted database.")
        with admin.connect() as connection:
            connection.execute(text('CREATE DATABASE "' + database_name + '"'))
        identity_engine = create_engine(admin.url.set(database=database_name), hide_parameters=True)
    else:
        identity_engine = create_engine(f"sqlite:///{(tmp_path / 'identities.db').as_posix()}", connect_args={"check_same_thread": False})
    mailbox = Mailbox()
    service = IdentityStore(settings, test_engine=identity_engine, mailer=mailbox)
    monkeypatch.setattr(HostedSettings, "load", classmethod(lambda cls: settings))
    monkeypatch.setattr(HostedSettings, "validate", lambda self: None)
    monkeypatch.setattr(main, "IdentityStore", lambda _: service)
    monkeypatch.setattr(main, "PUBLIC_DEMO", True)
    monkeypatch.setattr(main, "RUNTIME", tmp_path)
    monkeypatch.setattr(main, "Classifier", lambda **_: ml)
    with TestClient(main.app, base_url=ORIGIN) as browser:
        yield browser, service, mailbox
    if admin:
        with admin.connect() as connection:
            connection.execute(text('DROP DATABASE "' + database_name + '" WITH (FORCE)'))
        admin.dispose()


def enroll(browser, store, mail, email=ALICE):
    store.send_grant(email, "invite")
    token = mail.messages[-1][2]
    response = browser.post("/api/auth/register", headers={"Origin": ORIGIN}, json={"email": email, "password": PASSWORD, "invitation": token})
    assert response.status_code == 201, response.text
    return token


def login(browser, email=ALICE, password=PASSWORD):
    response = browser.post("/api/auth/login", headers={"Origin": ORIGIN}, json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    browser.headers.update({"Origin": ORIGIN, "X-Moniq-CSRF": response.json()["csrf_token"]})
    return response


def another_browser(first):
    return TestClient(first.app, base_url=ORIGIN)


def register_account(browser, name="Private checking", balance="10.00", last_four="1234"):
    response = browser.post("/api/gmail/accounts", json={"name": name, "account_type": "checking", "opening_balance": balance,
                                                        "last_four": last_four, "balance_date": config.today().isoformat()})
    assert response.status_code == 201, response.text
    return response.json()[-1]["id"]


def test_welcome_requires_explicit_demo_and_never_loads_owner(hosted_app):
    browser, store, _ = hosted_app
    before = len(main.app.state.demo_store.sessions)
    response = browser.get("/api/config")
    assert response.json()["workspace"] == "welcome"
    assert len(main.app.state.demo_store.sessions) == before
    assert browser.get("/api/dashboard").status_code == 401
    browser.cookies.set("moniq_workspace", "personal")
    assert browser.get("/api/gmail/status").status_code == 403
    assert browser.post("/api/demo/start", headers={"Origin": ORIGIN}, json={}).status_code == 200
    assert browser.get("/api/config").json()["workspace"] == "demo"
    assert browser.get("/api/dashboard").status_code == 200
    assert browser.get("/api/gmail/status").status_code == 403
    assert browser.post("/api/gmail/sync", headers={"Origin": ORIGIN}, json={}).status_code == 403
    assert not store.workspaces


def test_verified_invitation_login_cookies_csrf_logout_and_replay(hosted_app):
    browser, store, mail = hosted_app
    invitation = enroll(browser, store, mail)
    assert browser.post("/api/auth/register", headers={"Origin": ORIGIN}, json={"email": ALICE, "password": PASSWORD, "invitation": invitation}).status_code == 400
    response = login(browser)
    for cookie in response.headers.get_list("set-cookie"):
        assert "Secure" in cookie and "HttpOnly" in cookie and "SameSite=lax" in cookie and "Path=/" in cookie
    with Session(store.engine) as db:
        user = db.scalar(select(User))
        assert user.verified and user.password_hash.startswith("$argon2id$") and PASSWORD not in user.password_hash
        session = db.scalar(select(AuthSession))
        assert session.id == digest(browser.cookies.get(AUTH_COOKIE))
    assert browser.get("/api/config").json()["workspace"] == "personal"
    assert browser.get("/api/dashboard").json()["balance"] == 0
    assert browser.post("/api/demo/reset", json={}).status_code == 403
    assert browser.post("/api/upgrade-demo/start", json={}).status_code == 403
    csrf = browser.headers.pop("x-moniq-csrf")
    assert browser.post("/api/gmail/accounts", json={}).status_code == 403
    browser.headers["X-Moniq-CSRF"] = csrf
    token = browser.cookies.get(AUTH_COOKIE)
    assert browser.post("/api/auth/logout", json={}).status_code == 204
    assert store.authenticate(token) is None
    assert browser.get("/api/dashboard").status_code == 401


def test_cross_user_accounts_transactions_profile_and_demo_are_isolated(hosted_app):
    alice, store, mail = hosted_app
    enroll(alice, store, mail)
    enroll(alice, store, mail, BOB)
    login(alice)
    account = register_account(alice)
    saved = alice.post("/api/transactions", json={"account_id": account, "date": config.today().isoformat(), "merchant": "Private campus job", "description": "Private campus job", "amount": "400.00", "kind": "income", "category": "income"})
    assert saved.status_code == 201, saved.text
    assert alice.get("/api/dashboard").json()["balance"] == 410
    bob = another_browser(alice)
    login(bob, BOB)
    assert bob.get("/api/transactions").json() == []
    assert bob.get("/api/gmail/accounts").json() == []
    assert bob.get("/api/gmail/items").json() == []
    assert bob.delete(f"/api/transactions/{saved.json()['id']}").status_code == 404
    assert alice.get("/api/dashboard").json()["balance"] == 410
    assert alice.post("/api/workspace", json={"workspace": "demo"}).status_code == 200
    assert alice.get("/api/gmail/status").status_code == 403
    assert alice.post("/api/upgrade-demo/start", json={"starting_balance": "10.00"}).status_code == 200
    assert alice.get("/api/dashboard").json()["balance"] == 10
    assert alice.post("/api/workspace", json={"workspace": "personal"}).status_code == 200
    assert alice.get("/api/dashboard").json()["balance"] == 410


def test_recovery_single_use_replaces_password_revokes_sessions_and_states(hosted_app):
    browser, store, mail = hosted_app
    enroll(browser, store, mail)
    login(browser)
    session_token = browser.cookies.get(AUTH_COOKIE)
    assert browser.post("/api/gmail/connect", json={}).status_code == 200
    unknown = browser.post("/api/auth/recover", json={"email": "unknown@moniq.example.test"})
    known = browser.post("/api/auth/recover", json={"email": ALICE})
    assert unknown.status_code == known.status_code == 202 and unknown.json() == known.json()
    token = mail.messages[-1][2]
    assert mail.messages[-1][1] == "reset"
    new_password = "new synthetic password 456"
    assert browser.post("/api/auth/reset-password", json={"token": token, "password": new_password}).status_code == 200
    assert store.authenticate(session_token) is None
    with Session(store.engine) as db:
        assert not db.scalar(select(OAuthAttempt))
    assert browser.post("/api/auth/reset-password", json={"token": token, "password": new_password}).status_code == 400
    assert browser.post("/api/auth/login", json={"email": ALICE, "password": PASSWORD}).status_code == 401
    login(browser, password=new_password)


def test_origins_session_expiry_rate_limits_and_secret_validation(hosted_app):
    browser, store, mail = hosted_app
    assert browser.post("/api/auth/login", json={"email": ALICE, "password": PASSWORD}).status_code == 403
    assert browser.post("/api/auth/login", headers={"Origin": "https://evil.example.test"}, json={"email": ALICE, "password": PASSWORD}).status_code == 403
    enroll(browser, store, mail)
    login(browser)
    with Session(store.engine) as db:
        row = db.get(AuthSession, digest(browser.cookies.get(AUTH_COOKIE)))
        row.idle_expires = int(time.time()) - 1
        db.commit()
    assert browser.get("/api/dashboard").status_code == 401
    assert browser.get("/api/gmail/items").status_code == 403
    marker = "synthetic-password-must-not-be-reflected" * 6
    response = browser.post("/api/auth/login", json={"email": ALICE, "password": marker})
    assert response.status_code == 422 and marker not in response.text
    for _ in range(8):
        response = browser.post("/api/auth/login", json={"email": ALICE, "password": "incorrect"})
    assert response.status_code == 429


def test_oauth_state_is_bound_to_browser_user_and_session_single_use(hosted_app, monkeypatch):
    alice, store, mail = hosted_app
    enroll(alice, store, mail)
    enroll(alice, store, mail, BOB)
    login(alice)
    begin = alice.post("/api/gmail/connect", json={})
    query = parse_qs(urlsplit(begin.json()["authorization_url"]).query)
    state = query["state"][0]
    assert query["redirect_uri"] == [ORIGIN + "/api/gmail/callback"]
    assert query["scope"] == [config.GMAIL_SCOPE] and query["code_challenge_method"] == ["S256"]
    browser_cookie = alice.cookies.get("moniq_gmail_oauth")
    alice.cookies.set("moniq_gmail_oauth", "wrong-browser", domain="moniq.test", path="/api/gmail/callback")
    assert alice.get("/api/gmail/callback", params={"state": state, "code": "synthetic-code"}).status_code == 400
    alice.cookies.set("moniq_gmail_oauth", browser_cookie, domain="moniq.test", path="/api/gmail/callback")
    bob = another_browser(alice)
    login(bob, BOB)
    bob.cookies.set("moniq_gmail_oauth", alice.cookies.get("moniq_gmail_oauth"), domain="moniq.test", path="/api/gmail/callback")
    assert bob.get("/api/gmail/callback", params={"state": state, "code": "synthetic-code"}).status_code == 400
    response = alice.get("/api/gmail/callback", params={"state": state, "error": "access_denied"}, follow_redirects=False)
    assert response.status_code == 303 and response.headers["location"].endswith("/?gmail=denied#settings")
    assert alice.get("/api/gmail/callback", params={"state": state, "error": "access_denied"}).status_code == 400


def test_encrypted_tokens_are_user_bound_and_survive_store_restart(hosted_app):
    browser, store, mail = hosted_app
    enroll(browser, store, mail)
    enroll(browser, store, mail, BOB)
    login(browser)
    identity = store.authenticate(browser.cookies.get(AUTH_COOKIE))
    vault = DatabaseVault(store, identity.user_id)
    value = {"email": ALICE, "mailbox_key": digest(ALICE), "token": {"access_token": "synthetic-access-token", "refresh_token": "synthetic-refresh-token", "expires_at": time.time() + 3600}}
    vault.save(value)
    with Session(store.engine) as db:
        row = db.get(GmailCredential, identity.user_id)
        assert b"synthetic-access-token" not in row.ciphertext and ALICE.encode() not in row.ciphertext
        bob = db.scalar(select(User).where(User.email == BOB))
        db.add(GmailCredential(user_id=bob.id, ciphertext=row.ciphertext))
        db.commit()
        bob_id = bob.id
    with pytest.raises(HTTPException) as failure:
        DatabaseVault(store, bob_id).load()
    assert failure.value.status_code == 503
    reopened = IdentityStore(store.settings, test_engine=store.engine, mailer=mail)
    assert DatabaseVault(reopened, identity.user_id).load() == value
    wrong_key_store = type("WrongKey", (), {"engine": store.engine, "settings": replace(store.settings, gmail_key=Fernet.generate_key().decode())})()
    with pytest.raises(HTTPException):
        DatabaseVault(wrong_key_store, identity.user_id).load()


def message(identifier, text):
    return {"id": identifier, "internalDate": str(int(time.time() * 1000)), "payload": {"mimeType": "text/plain", "headers": [{"name": "Subject", "value": "Confirmed financial alert"}, {"name": "From", "value": "Synthetic bank <alerts@bank.example.test>"}], "body": {"data": base64.urlsafe_b64encode(text.encode()).decode()}}}


def test_private_gmail_sync_approvals_balance_forecast_duplicates_and_disconnect(hosted_app, monkeypatch):
    browser, store, mail = hosted_app
    enroll(browser, store, mail)
    login(browser)
    account = register_account(browser)
    identity = store.authenticate(browser.cookies.get(AUTH_COOKIE))
    DatabaseVault(store, identity.user_id).save({"email": ALICE, "mailbox_key": digest(ALICE), "token": {"access_token": "synthetic-access-token", "refresh_token": "synthetic-refresh-token", "expires_at": time.time() + 3600}})
    day = config.today().isoformat()
    emails = {"pay1": message("pay1", f"Confirmed paycheck deposit of $400.00 from Campus job payroll on {day}. Account ending in 1234."),
              "buy1": message("buy1", f"Posted purchase of $15.00 at Chick-fil-A on {day}. Card ending in 1234.")}
    def gmail_api(self, token, path, params=None):
        assert self.identity.user_id == identity.user_id and token["access_token"] == "synthetic-access-token"
        return {"messages": [{"id": key} for key in emails]} if path == "/messages" else emails[path.rsplit("/", 1)[1]]
    monkeypatch.setattr(HostedGmailManager, "api", gmail_api)
    monkeypatch.setattr(HostedGmailManager, "revoke", staticmethod(lambda token: True))
    assert browser.post("/api/gmail/sync", json={}).json()["queued"] == 2
    assert browser.get("/api/dashboard").json()["balance"] == 10
    queue = browser.get("/api/approvals").json()["items"]
    for kind, expected in (("income", 410), ("purchase", 395)):
        item = next(row for row in queue if row["event_type"] == kind)
        payload = {"account_id": account, "date": item["date"], "description": item["merchant"], "merchant": item["merchant"], "amount": str(item["amount"]), "category": item["category"], "kind": "income" if kind == "income" else "expense", "posted_confirmed": True}
        saved = browser.post(f"/api/approvals/{item['id']}/confirm", json=payload)
        assert saved.status_code == 200, saved.text
        assert browser.get("/api/dashboard").json()["balance"] == expected
        assert browser.post(f"/api/approvals/{item['id']}/confirm", json=payload).status_code == 409
    assert browser.post("/api/gmail/sync", json={}).json()["already_seen"] == 2
    assert len(browser.get("/api/transactions").json()) == 2
    assert browser.get("/api/forecast").status_code == 200
    summary = browser.get("/api/smartapprove/summary")
    assert summary.status_code == 200 and len(summary.json()["history"]) == 2
    assert browser.post("/api/gmail/disconnect", json={}).json()["google_revoked"]
    assert browser.get("/api/gmail/status").json()["connected"] is False
    assert browser.get("/api/dashboard").json()["balance"] == 395


def test_anonymous_simulated_gmail_flow_manual_approvals_only(hosted_app, monkeypatch):
    browser, _, _ = hosted_app
    monkeypatch.setattr(HostedGmailManager, "api", lambda *args, **kwargs: pytest.fail("Demo must never call Gmail"))
    browser.headers["Origin"] = ORIGIN
    browser.post("/api/demo/start", json={})
    assert browser.post("/api/upgrade-demo/start", json={"starting_balance": "10.00"}).status_code == 200
    for event, expected in (("paycheck", 410), ("purchase", 395)):
        response = browser.post("/api/upgrade-demo/financial-alert", json={"event": event})
        assert response.status_code == 200, response.text
        item = response.json()
        payload = {"account_id": item["account_id"], "date": item["date"], "description": item["merchant"], "merchant": item["merchant"], "amount": str(item["amount"]), "category": item["category"], "kind": "income" if event == "paycheck" else "expense", "posted_confirmed": True}
        assert browser.post(f"/api/approvals/{item['id']}/confirm", json=payload).status_code == 200
        assert browser.get("/api/dashboard").json()["balance"] == expected
    assert browser.post("/api/gmail/sync", json={}).status_code == 403
    assert browser.get("/api/export").json()["synthetic"] is True


def test_private_configuration_fails_closed_without_persistence_recovery_https_or_key():
    basic = HostedSettings(enabled=True, origin=ORIGIN)
    basic.validate()  # Welcome and demo need no credentials or paid database.
    with pytest.raises(ValueError):
        replace(basic, private_enabled=True).validate()
    with pytest.raises(ValueError):
        replace(basic, origin="http://moniq.test").validate()
    with pytest.raises(ValueError):
        replace(basic, private_enabled=True, persistence_verified=True, recovery_verified=True, database_url="sqlite:///private.db").validate()


def test_successful_hosted_exchange_rejects_other_mailbox_and_revoked_session(hosted_app, monkeypatch):
    browser, store, mail = hosted_app
    enroll(browser, store, mail)
    login(browser)
    class SyntheticExchange:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def fetch_token(self, *args, **kwargs):
            assert kwargs.get("code_verifier")
            return {"access_token": "synthetic-access", "refresh_token": "synthetic-refresh", "scope": config.GMAIL_SCOPE, "expires_at": time.time() + 3600}
    begin = browser.post("/api/gmail/connect", json={})
    state = parse_qs(urlsplit(begin.json()["authorization_url"]).query)["state"][0]
    original_oauth_client = HostedGmailManager.oauth_client
    monkeypatch.setattr(HostedGmailManager, "oauth_client", lambda *args, **kwargs: SyntheticExchange())
    monkeypatch.setattr(HostedGmailManager, "api", lambda *args, **kwargs: {"emailAddress": ALICE})
    response = browser.get("/api/gmail/callback", params={"state": state, "code": "synthetic-code"}, follow_redirects=False)
    assert response.status_code == 303 and "gmail=connected" in response.headers["location"]
    assert browser.get("/api/gmail/status").json()["email"] == ALICE
    identity = store.authenticate(browser.cookies.get(AUTH_COOKIE))
    service = HostedGmailManager(store, identity)
    # A second mailbox must not replace the existing user's connection.
    monkeypatch.setattr(HostedGmailManager, "oauth_client", original_oauth_client)
    state = parse_qs(urlsplit(service.begin()[0]).query)["state"][0]
    with Session(store.engine) as db:
        pending = db.get(OAuthAttempt, digest(state))
        pending.browser_digest = digest("synthetic-browser")
        db.commit()
    monkeypatch.setattr(HostedGmailManager, "oauth_client", lambda *args, **kwargs: SyntheticExchange())
    monkeypatch.setattr(HostedGmailManager, "api", lambda *args, **kwargs: {"emailAddress": BOB})
    monkeypatch.setattr(HostedGmailManager, "revoke", staticmethod(lambda token: True))
    with pytest.raises(HTTPException) as failure:
        service.finish(state, "synthetic-browser", "synthetic-code")
    assert failure.value.status_code == 403
    assert service.vault.load()["email"] == ALICE
    store.logout(browser.cookies.get(AUTH_COOKIE))
    assert browser.get("/api/gmail/callback", params={"state": state, "code": "synthetic-code"}).status_code == 403


def test_hosted_private_account_tools_circles_goals_and_smartapprove_scope(hosted_app):
    browser, store, mail = hosted_app
    enroll(browser, store, mail)
    login(browser)
    account = register_account(browser)
    assert browser.get("/api/accounts").json()[0]["id"] == account
    card = browser.post(f"/api/accounts/{account}/debit-cards", json={"name": "Private debit", "last_four": "6789"})
    assert card.status_code == 201, card.text
    assert browser.put("/api/goals/1", json={"name": "My private textbook fund", "target": 100, "saved": 10}).status_code == 200
    circle = browser.post("/api/circles", json={"name": "Private study group", "kind": "friends", "currency": "USD", "participants": ["Student", "Private friend"]})
    assert circle.status_code == 201, circle.text
    rule = browser.post("/api/smartapprove/rules", json={"sender": "alerts@private-bank.example.test", "match_type": "address", "institution": "Private test bank", "account_id": account, "events": ["purchase"], "enabled": False, "transaction_limit": "20.00", "daily_limit": "50.00"})
    assert rule.status_code == 201, rule.text
    assert browser.post("/api/workspace", json={"workspace": "demo"}).status_code == 200
    assert browser.get("/api/smartapprove/rules").json() == []
    assert browser.get("/api/circles").json() == []


def test_private_ledger_survives_a_fresh_store_and_migrations_are_idempotent(hosted_app):
    browser, store, mail = hosted_app
    enroll(browser, store, mail)
    login(browser)
    account = register_account(browser, balance="395.00")
    original = store.authenticate(browser.cookies.get(AUTH_COOKIE))
    reopened = IdentityStore(store.settings, test_engine=create_engine(store.engine.url, hide_parameters=True), mailer=mail)
    restored = reopened.authenticate(browser.cookies.get(AUTH_COOKIE))
    assert restored == original
    from backend.app.models import Account
    with Session(reopened.workspace(restored.user_id)) as db:
        assert db.get(Account, account).opening_balance_cents == 39500
    reopened.close()


def test_https_verification_email_uses_fixed_endpoint_and_fragment_token(monkeypatch):
    requests = []
    class FakeMailClient:
        def __init__(self, **kwargs):
            assert kwargs["follow_redirects"] is False
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def post(self, url, **kwargs):
            requests.append((url, kwargs))
            return type("Accepted", (), {"status_code": 200})()
    monkeypatch.setattr("backend.app.identity.httpx.Client", FakeMailClient)
    settings = HostedSettings(origin=ORIGIN, mail_transport="resend", mail_api_key="synthetic-mail-key", mail_from="Moniq <verify@moniq.example.test>")
    TLSMailer(settings).send(ALICE, "reset", "synthetic-reset-token")
    url, sent = requests[0]
    assert url == "https://api.resend.com/emails" and sent["headers"]["Authorization"] == "Bearer synthetic-mail-key"
    assert sent["json"]["to"] == [ALICE]
    assert ORIGIN + "/#reset=synthetic-reset-token" in sent["json"]["text"]
    assert "synthetic-mail-key" not in sent["json"]["text"]
