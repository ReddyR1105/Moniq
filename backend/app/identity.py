"""Closed enrollment, hashed passwords, opaque sessions and durable workspace routing."""
import hashlib
import hmac
import re
import secrets
import smtplib
import ssl
import time
import uuid
import httpx
from dataclasses import dataclass
from email.message import EmailMessage
from threading import RLock

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import HTTPException
from sqlalchemy import create_engine, delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from .identity_models import AuthSession, EmailGrant, OAuthAttempt, RateBucket, User
from .migrations import migrate_identity, migrate_workspace
from .models import Profile

AUTH_COOKIE = "__Host-moniq_session"
MODE_COOKIE = "__Host-moniq_mode"
SESSION_SECONDS = 43200
IDLE_SECONDS = 1800
PASSWORDS = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=1)
DUMMY_PASSWORD = PASSWORDS.hash(secrets.token_urlsafe(32))


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def normalize_email(value):
    value = value.strip().casefold()
    if len(value) > 254 or not re.fullmatch(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,}", value):
        raise HTTPException(422, "Use a valid email address.")
    return value


def password_value(value):
    if not 15 <= len(value) <= 128:
        raise HTTPException(422, "Use a password or passphrase of 15–128 characters.")
    return value


class TLSMailer:
    def __init__(self, settings):
        self.settings = settings

    def send(self, email, purpose, token):
        settings = self.settings
        message = EmailMessage()
        message["From"], message["To"] = settings.mail_from, email
        message["Subject"] = "Moniq: " + ("your private test invitation" if purpose == "invite" else "reset your password")
        # Fragment tokens stay out of HTTP access logs and Referer headers.
        message.set_content(f"Open {settings.origin}/#{purpose}={token}\nThis one-time link expires shortly. Ignore it if you did not request it.")
        context = ssl.create_default_context()
        if settings.mail_transport == "resend":
            # Fixed official HTTPS endpoint. No user-supplied URLs, redirects or logs.
            with httpx.Client(timeout=15, follow_redirects=False) as client:
                response = client.post("https://api.resend.com/emails", headers={"Authorization": "Bearer " + settings.mail_api_key},
                                       json={"from": settings.mail_from, "to": [email], "subject": message["Subject"], "text": message.get_content()})
            if response.status_code not in {200, 201}:
                raise RuntimeError("Verification email provider did not accept the message.")
            return
        if settings.smtp_port == 465:
            connection = smtplib.SMTP_SSL(settings.smtp_host, 465, timeout=15, context=context)
        else:
            connection = smtplib.SMTP(settings.smtp_host, 587, timeout=15)
        with connection as smtp:
            if settings.smtp_port == 587:
                smtp.starttls(context=context)
            smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)


@dataclass(frozen=True)
class Identity:
    user_id: str
    email: str
    session_id: str


class IdentityStore:
    def __init__(self, settings, *, test_engine=None, mailer=None):
        self.settings = settings
        if test_engine is None:
            settings.validate()
            url = re.sub(r"^postgres(?:ql)?://", "postgresql+psycopg://", settings.database_url)
            self.engine = create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=5, hide_parameters=True)
        else:
            # Explicit dependency injection is available only to tests, never environment switches.
            self.engine = test_engine
        migrate_identity(self.engine)
        self.mailer = mailer or TLSMailer(settings)
        self.lock = RLock()
        self.workspaces = {}
        self.classifiers = {}
        self.gmail_locks = {}

    def rate_limit(self, action, identifier, limit=10, seconds=900):
        key = hmac.new(self.settings.session_key.encode(), (action + ":" + identifier).encode(), hashlib.sha256).hexdigest()
        now = int(time.time())
        with self.lock, Session(self.engine) as db:
            # Persisted counters; concurrent workers use one atomic UPSERT.
            if self.engine.dialect.name == "postgresql":
                from sqlalchemy import case
                stmt = pg_insert(RateBucket).values(key=key, count=1, expires=now + seconds)
                stmt = stmt.on_conflict_do_update(index_elements=[RateBucket.key], set_={
                    "count": case((RateBucket.expires <= now, 1), else_=RateBucket.count + 1),
                    "expires": case((RateBucket.expires <= now, now + seconds), else_=RateBucket.expires)})
                count = db.scalar(stmt.returning(RateBucket.count))
            else:
                row = db.get(RateBucket, key)
                if row is None:
                    row = RateBucket(key=key, count=0, expires=now + seconds)
                    db.add(row)
                if row.expires <= now:
                    row.count, row.expires = 0, now + seconds
                row.count += 1
                count = row.count
            db.execute(delete(RateBucket).where(RateBucket.expires < now - 86400))
            db.commit()
        if count > limit:
            raise HTTPException(429, "Too many attempts. Try again later.", headers={"Retry-After": str(seconds)})

    def send_grant(self, email, purpose):
        email = normalize_email(email)
        if email not in self.settings.allowed_emails:
            return
        if purpose == "reset":
            with Session(self.engine) as db:
                if not db.scalar(select(User.id).where(User.email == email, User.verified.is_(True), User.enabled.is_(True))):
                    return
        token = secrets.token_urlsafe(32)
        with Session(self.engine) as db:
            db.execute(delete(EmailGrant).where(EmailGrant.email == email, EmailGrant.purpose == purpose))
            db.execute(delete(EmailGrant).where(EmailGrant.expires < int(time.time())))
            db.add(EmailGrant(digest=digest(token), email=email, purpose=purpose, expires=int(time.time()) + (3600 if purpose == "invite" else 1200)))
            db.commit()
        try:
            self.mailer.send(email, purpose, token)
        except Exception:
            with Session(self.engine) as db:
                db.execute(delete(EmailGrant).where(EmailGrant.digest == digest(token)))
                db.commit()
            raise HTTPException(503, "Verification email delivery is unavailable. Try again later.") from None

    def register(self, email, password, token):
        email = normalize_email(email)
        password_hash = PASSWORDS.hash(password_value(password))
        with self.lock, Session(self.engine) as db:
            grant = db.scalar(select(EmailGrant).where(EmailGrant.digest == digest(token)).with_for_update())
            if email not in self.settings.allowed_emails or not grant or grant.email != email or grant.purpose != "invite" or grant.expires <= time.time():
                raise HTTPException(400, "Invitation is invalid or expired. Use the link sent to your invited email.")
            if db.scalar(select(User.id).where(User.email == email)):
                raise HTTPException(400, "Use Log In or password recovery for this invitation.")
            user_id = uuid.uuid4().hex
            # Create only this new empty workspace, never seed personal accounts with Alex's records.
            self.workspace(user_id)
            db.add(User(id=user_id, email=email, password_hash=password_hash, verified=True, enabled=True))
            db.delete(grant)
            db.commit()
        return {"verified": True, "message": "Account created and email verified. You can log in."}

    def login(self, email, password):
        email = normalize_email(email)
        with Session(self.engine) as db:
            user = db.scalar(select(User).where(User.email == email))
            try:
                correct = PASSWORDS.verify(user.password_hash if user else DUMMY_PASSWORD, password)
            except (VerificationError, InvalidHashError):
                correct = False
            if not correct or not user or not user.enabled or not user.verified or email not in self.settings.allowed_emails:
                raise HTTPException(401, "Email or password is incorrect, or this account is unavailable.")
            if PASSWORDS.check_needs_rehash(user.password_hash):
                user.password_hash = PASSWORDS.hash(password)
            token = secrets.token_urlsafe(32)
            now = int(time.time())
            db.execute(delete(AuthSession).where(AuthSession.expires <= now))
            db.add(AuthSession(id=digest(token), user_id=user.id, expires=now + SESSION_SECONDS, idle_expires=now + IDLE_SECONDS))
            db.commit()
        return token

    def authenticate(self, token):
        if not token or len(token) > 100:
            return None
        now = int(time.time())
        with Session(self.engine) as db:
            session = db.get(AuthSession, digest(token))
            if not session or min(session.expires, session.idle_expires) <= now:
                return None
            user = db.get(User, session.user_id)
            if not user or not user.enabled or not user.verified or user.email not in self.settings.allowed_emails:
                return None
            session.idle_expires = min(now + IDLE_SECONDS, session.expires)
            identity = Identity(user.id, user.email, session.id)
            db.commit()
            return identity

    def csrf(self, token):
        return hmac.new(self.settings.session_key.encode(), ("csrf:" + token).encode(), hashlib.sha256).hexdigest()

    def logout(self, token):
        with Session(self.engine) as db:
            session_id = digest(token)
            db.execute(delete(OAuthAttempt).where(OAuthAttempt.session_id == session_id))
            db.execute(delete(AuthSession).where(AuthSession.id == session_id))
            db.commit()

    def reset_password(self, token, password):
        password_hash = PASSWORDS.hash(password_value(password))
        with self.lock, Session(self.engine) as db:
            grant = db.scalar(select(EmailGrant).where(EmailGrant.digest == digest(token)).with_for_update())
            if not grant or grant.purpose != "reset" or grant.expires <= time.time():
                raise HTTPException(400, "Password reset link is invalid or expired.")
            user = db.scalar(select(User).where(User.email == grant.email, User.enabled.is_(True)))
            if not user:
                raise HTTPException(400, "Password reset link is invalid or expired.")
            user.password_hash = password_hash
            sessions = select(AuthSession.id).where(AuthSession.user_id == user.id)
            db.execute(delete(OAuthAttempt).where(OAuthAttempt.session_id.in_(sessions)))
            db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
            db.execute(delete(EmailGrant).where(EmailGrant.email == user.email))
            db.commit()

    def workspace(self, user_id):
        if not re.fullmatch(r"[0-9a-f]{32}", user_id):
            raise HTTPException(403, "Invalid workspace identity.")
        with self.lock:
            if user_id not in self.workspaces:
                if self.engine.dialect.name == "postgresql":
                    owned = self.engine.execution_options(schema_translate_map={None: "moniq_user_" + user_id})
                    migrate_workspace(owned, "moniq_user_" + user_id)
                else:
                    # Test adapter requires separate databases too, never a shared SQLite ledger.
                    from pathlib import Path
                    path = Path(self.engine.url.database).parent / ("workspace-" + user_id + ".db")
                    owned = create_engine("sqlite:///" + path.as_posix(), connect_args={"check_same_thread": False})
                    migrate_workspace(owned)
                with Session(owned) as db:
                    if not db.get(Profile, 1):
                        db.add(Profile(id=1, name="Student", university="Not set", allowance_cents=0, student_verified=False))
                        db.commit()
                self.workspaces[user_id] = owned
            return self.workspaces[user_id]

    def close(self):
        for owned in self.workspaces.values():
            owned.dispose()
        self.engine.dispose()
