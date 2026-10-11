"""Test explicit migration using a synthetic registered ledger and disposable PostgreSQL."""
import os
from pathlib import Path
import secrets
import subprocess
import sys
import uuid
from datetime import date

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from backend.app.hosted_settings import HostedSettings
from backend.app.identity import IdentityStore, PASSWORDS, digest
from backend.app.identity_models import User
from backend.app.models import Account, AccountDetails, Base, Profile, Transaction


def test_offline_migration_preserves_cents_fingerprints_ids_and_serial_sequences(tmp_path):
    postgres = os.getenv("MONIQ_TEST_POSTGRES_URL")
    if not postgres:
        pytest.skip("Requires a disposable local PostgreSQL cluster.")
    admin = create_engine(postgres, isolation_level="AUTOCOMMIT", hide_parameters=True)
    assert admin.url.host in {"127.0.0.1", "localhost"} and admin.url.database == "postgres"
    name = "moniq_test_import_" + uuid.uuid4().hex
    with admin.connect() as connection:
        connection.execute(text('CREATE DATABASE "' + name + '"'))
    url = admin.url.set(database=name)
    destination = create_engine(url, hide_parameters=True)
    source_path = tmp_path / "synthetic-personal.db"
    source = create_engine("sqlite:///" + source_path.as_posix())
    Base.metadata.create_all(source)
    user_id = uuid.uuid4().hex
    email = "migration@moniq.example.test"
    session_key = secrets.token_urlsafe(48)
    settings = HostedSettings(enabled=True, private_enabled=True, origin="https://moniq.test", session_key=session_key, allowed_emails=(email,))
    store = IdentityStore(settings, test_engine=destination)
    try:
        with Session(destination) as db:
            store.workspace(user_id)
            db.add(User(id=user_id, email=email, password_hash=PASSWORDS.hash("synthetic migration password 123"), verified=True, enabled=True))
            db.commit()
        with Session(source) as db:
            db.add(Profile(id=1, name="Synthetic migration student", allowance_cents=0))
            db.add(Account(id=9, name="Synthetic registered checking", mode="registered", opening_balance_cents=1000))
            db.flush()
            db.add(AccountDetails(account_id=9, account_type="checking", last_four="1234", balance_date=date.today()))
            db.add_all([Transaction(id=8, account_id=9, date=date.today(), description="Synthetic paycheck", merchant="Campus job", amount_cents=40000, kind="income", category="income", source="gmail", fingerprint=digest("synthetic-paycheck")),
                        Transaction(id=22, account_id=9, date=date.today(), description="Synthetic purchase", merchant="Campus cafe", amount_cents=-1500, kind="expense", category="food", source="gmail", fingerprint=digest("synthetic-purchase"))])
            db.commit()
        environment = {**os.environ, "HOSTED_DATABASE_URL": url.render_as_string(hide_password=False), "MONIQ_HOSTED_APP": "true", "MONIQ_PRIVATE_ACCOUNTS_ENABLED": "true",
                       "MONIQ_PUBLIC_ORIGIN": settings.origin, "MONIQ_SESSION_SIGNING_KEY": session_key, "MONIQ_TEST_USER_EMAILS": email,
                       "MONIQ_PERSISTENCE_VERIFIED": "true", "MONIQ_RECOVERY_VERIFIED": "true", "MONIQ_SMTP_HOST": "smtp.moniq.example.test", "MONIQ_SMTP_PORT": "465", "MONIQ_SMTP_USER": "synthetic", "MONIQ_SMTP_PASSWORD": "synthetic-mail-only", "MONIQ_MAIL_FROM": email,
                       "MONIQ_HOSTED_GMAIL_ENABLED": "false", "MONIQ_GMAIL_DISABLED": "true", "GMAIL_CLIENT_ID": "", "GMAIL_CLIENT_SECRET": "", "GMAIL_TOKEN_ENCRYPTION_KEY": ""}
        command = [sys.executable, "scripts/import-private-workspace.py", "--source", str(source_path), "--email", email]
        dry = subprocess.run(command, env=environment, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=30)
        assert dry.returncode == 0, dry.stderr
        assert "Dry run only" in dry.stdout
        copied = subprocess.run([*command, "--copy"], env=environment, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=30)
        assert copied.returncode == 0, copied.stderr
        with Session(store.workspace(user_id)) as db:
            rows = list(db.scalars(select(Transaction).order_by(Transaction.id)))
            assert [row.id for row in rows] == [8, 22]
            assert [row.amount_cents for row in rows] == [40000, -1500]
            assert db.get(Account, 9).opening_balance_cents + sum(row.amount_cents for row in rows) == 39500
            extra = Account(name="Another synthetic registered account", mode="registered", opening_balance_cents=0)
            db.add(extra)
            db.flush()
            assert extra.id == 10
            db.rollback()
        with Session(source) as db:
            assert len(list(db.scalars(select(Transaction)))) == 2  # Read-only source preserved.
        refused = subprocess.run([*command, "--copy"], env=environment, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=30)
        assert refused.returncode != 0 and "Copy was refused" in refused.stderr
    finally:
        source.dispose()
        store.close()
        with admin.connect() as connection:
            connection.execute(text('DROP DATABASE "' + name + '" WITH (FORCE)'))
        admin.dispose()
