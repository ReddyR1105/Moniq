"""Explicit backend administration. Never prints credentials or invitation tokens."""
import argparse
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app import config  # noqa: E402, F401 - loads local .env without displaying it
from backend.app.hosted_settings import HostedSettings  # noqa: E402
from backend.app.identity import IdentityStore, normalize_email  # noqa: E402
from backend.app.identity_models import AuthSession, OAuthAttempt, User  # noqa: E402
from backend.app.migrations import migrate_identity  # noqa: E402
from sqlalchemy import create_engine, delete, select, text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

parser = argparse.ArgumentParser(description=__doc__)
sub = parser.add_subparsers(dest="action", required=True)
sub.add_parser("migrate", help="Apply identity and existing workspace migrations; does not enable accounts.")
invite = sub.add_parser("invite", help="Send a one-time invitation to an allowlisted test email.")
invite.add_argument("email")
revoke = sub.add_parser("revoke-sessions", help="Revoke all sessions for one verified test account.")
revoke.add_argument("email")
args = parser.parse_args()

if args.action == "migrate":
    value = os.getenv("HOSTED_DATABASE_URL", "")
    if not value.startswith(("postgres://", "postgresql://", "postgresql+psycopg://")):
        raise SystemExit("Configure a PostgreSQL HOSTED_DATABASE_URL privately on the backend.")
    owned = create_engine(re.sub(r"^postgres(?:ql)?://", "postgresql+psycopg://", value), hide_parameters=True, pool_pre_ping=True)
    try:
        migrate_identity(owned)
        with Session(owned) as db:
            users = list(db.scalars(select(User.id)))
        from backend.app.migrations import migrate_workspace
        for user_id in users:
            if not re.fullmatch(r"[0-9a-f]{32}", user_id):
                raise SystemExit("Migration stopped: an invalid workspace identity requires investigation.")
            schema = "moniq_user_" + user_id
            migrate_workspace(owned.execution_options(schema_translate_map={None: schema}), schema)
        with owned.connect() as connection:
            connection.execute(text("SELECT 1"))
        print(f"PostgreSQL identity and {len(users)} workspace migrations verified. Accounts were not enabled.")
    except Exception:
        raise SystemExit("PostgreSQL migration failed. Review backend configuration privately; credential values are not printed.") from None
    finally:
        owned.dispose()
else:
    settings = HostedSettings.load()
    if not settings.private_enabled:
        raise SystemExit("Enable only the verified private test configuration before inviting or administering accounts.")
    service = IdentityStore(settings)
    try:
        email = normalize_email(args.email)
        if email not in settings.allowed_emails:
            raise SystemExit("This address is not on the backend test-user allowlist.")
        if args.action == "invite":
            service.send_grant(email, "invite")
            print("Invitation sent over the configured TLS mail transport. No token was printed.")
        else:
            with Session(service.engine) as db:
                user_id = db.scalar(select(User.id).where(User.email == email))
                if user_id:
                    db.execute(delete(OAuthAttempt).where(OAuthAttempt.user_id == user_id))
                    db.execute(delete(AuthSession).where(AuthSession.user_id == user_id))
                    db.commit()
            print("Account sessions revoked. Financial records and Gmail credentials were preserved.")
    finally:
        service.close()
