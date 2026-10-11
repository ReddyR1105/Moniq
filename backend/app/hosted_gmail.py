"""Per-user PostgreSQL vault and session-bound, single-use PKCE OAuth state."""
import hashlib
import json
import secrets
import time

from authlib.integrations.httpx_client import OAuth2Client
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException
from httpx import Client as HTTPClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from . import config
from .gmail_service import AUTH_URL, REVOKE_URL, TOKEN_URL, GmailManager
from .identity import digest
from .identity_models import GmailCredential, OAuthAttempt


class DatabaseVault:
    def __init__(self, store, user_id):
        self.engine, self.user_id = store.engine, user_id
        self.cipher = Fernet(store.settings.gmail_key.encode())

    def encrypt(self, value):
        return self.cipher.encrypt(json.dumps({"owner": self.user_id, "value": value}).encode())

    def decrypt(self, value):
        try:
            decoded = json.loads(self.cipher.decrypt(value))
            if not secrets.compare_digest(decoded["owner"], self.user_id):
                raise ValueError("wrong owner")
            return decoded["value"]
        except (InvalidToken, ValueError, KeyError, TypeError):
            raise HTTPException(503, "The private Gmail vault cannot be decrypted. Restore the stable key or reconnect Gmail.") from None

    def load(self):
        with Session(self.engine) as db:
            row = db.get(GmailCredential, self.user_id)
            return self.decrypt(row.ciphertext) if row else None

    def save(self, value):
        ciphertext = self.encrypt(value)
        with Session(self.engine) as db:
            row = db.get(GmailCredential, self.user_id)
            if row:
                row.ciphertext = ciphertext
            else:
                db.add(GmailCredential(user_id=self.user_id, ciphertext=ciphertext))
            db.commit()

    def delete(self):
        with Session(self.engine) as db:
            db.execute(delete(GmailCredential).where(GmailCredential.user_id == self.user_id))
            db.execute(delete(OAuthAttempt).where(OAuthAttempt.user_id == self.user_id))
            db.commit()


class HostedGmailManager(GmailManager):
    def __init__(self, store, identity):
        super().__init__()
        self.store, self.identity, self.settings = store, identity, store.settings
        with store.lock:
            self.lock = store.gmail_locks.setdefault(identity.user_id, self.lock)

    def configured(self):
        return self.settings.gmail_enabled

    def ready(self):
        if not self.configured():
            raise HTTPException(503, "Hosted Gmail is not enabled for private testing yet.")
        if self.vault is None:
            self.vault = DatabaseVault(self.store, self.identity.user_id)

    def oauth_client(self, token=None):
        return OAuth2Client(self.settings.gmail_client_id, self.settings.gmail_client_secret,
                            token_endpoint_auth_method="client_secret_post", scope=config.GMAIL_SCOPE,
                            redirect_uri=self.settings.redirect_uri, code_challenge_method="S256", token=token,
                            timeout=20, follow_redirects=False)

    def begin(self):
        self.ready()
        self.store.rate_limit("gmail-connect", self.identity.user_id, limit=10)
        state, browser, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(32), secrets.token_urlsafe(64)
        with Session(self.store.engine) as db:
            db.execute(delete(OAuthAttempt).where(OAuthAttempt.expires <= int(time.time())))
            db.add(OAuthAttempt(digest=digest(state), user_id=self.identity.user_id, session_id=self.identity.session_id,
                                browser_digest=digest(browser), verifier=self.vault.encrypt(verifier), expires=int(time.time()) + 600))
            db.commit()
        with self.oauth_client() as oauth:
            url, _ = oauth.create_authorization_url(AUTH_URL, state=state, code_verifier=verifier,
                                                    access_type="offline", prompt="consent select_account", include_granted_scopes="false")
        return url, browser

    def finish(self, state, browser, code, error=None):
        self.ready()
        if not state or not browser or len(state) > 100 or len(browser) > 100:
            raise HTTPException(400, "Invalid OAuth state. Start Connect Gmail again.")
        with self.lock, Session(self.store.engine) as db:
            pending = db.scalar(select(OAuthAttempt).where(OAuthAttempt.digest == digest(state)).with_for_update())
            if not pending or pending.expires <= time.time() or pending.user_id != self.identity.user_id or pending.session_id != self.identity.session_id or not secrets.compare_digest(pending.browser_digest, digest(browser)):
                raise HTTPException(400, "Invalid, expired or wrong-session OAuth state. Start Connect Gmail again.")
            verifier = self.vault.decrypt(pending.verifier)
            db.delete(pending)
            db.commit()  # Consume before exchanging, including denial and provider failure.
            if error:
                return "denied"
            if not code:
                raise HTTPException(400, "Google did not return an authorization code.")
            try:
                with self.oauth_client() as oauth:
                    token = dict(oauth.fetch_token(TOKEN_URL, code=code, code_verifier=verifier))
                if set(token.get("scope", "").split()) != {config.GMAIL_SCOPE} or not token.get("refresh_token") or not token.get("access_token"):
                    raise HTTPException(400, "Grant only Gmail read-only and offline access, then reconnect.")
                profile = self.api(token, "/profile")
                email = profile.get("emailAddress", "").casefold()
                if email != self.identity.email or email not in self.settings.allowed_emails:
                    self.revoke(token)
                    raise HTTPException(403, "Choose the explicitly authorized Gmail address belonging to your verified Moniq account.")
                self.vault.save({"email": email, "mailbox_key": hashlib.sha256(email.encode()).hexdigest(), "token": token})
                return "connected"
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(502, "Google authorization exchange failed. Start Connect Gmail again.") from None

    @staticmethod
    def revoke(token):
        try:
            with HTTPClient(timeout=15, follow_redirects=False) as client:
                response = client.post(REVOKE_URL, data={"token": token.get("refresh_token") or token["access_token"]})
            return response.status_code == 200
        except Exception:
            return False

    def disconnect(self):
        with self.lock:
            revoked = True
            try:
                self.ready()
                stored = self.vault.load()
                if stored:
                    revoked = self.revoke(stored["token"])
            except HTTPException:
                revoked = False
            finally:
                # Always remove only this user's credential. Never touch the local owner's vault.
                with Session(self.store.engine) as db:
                    db.execute(delete(GmailCredential).where(GmailCredential.user_id == self.identity.user_id))
                    db.execute(delete(OAuthAttempt).where(OAuthAttempt.user_id == self.identity.user_id))
                    db.commit()
            return revoked
