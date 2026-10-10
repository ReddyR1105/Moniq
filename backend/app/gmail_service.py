"""Backend-only OAuth, encrypted tokens and bounded official Gmail API reads."""
import hashlib
import json
import secrets
import time
from pathlib import Path
from threading import RLock
from urllib.parse import urlsplit

import httpx
from httpx import Client as HTTPClient
from authlib.integrations.httpx_client import OAuth2Client
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException

from . import config
from .local_secrets import protect_local_path

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
API_URL = "https://gmail.googleapis.com/gmail/v1/users/me"
STATE_COOKIE = "moniq_gmail_oauth"


def configuration():
    callback, frontend = urlsplit(config.GMAIL_REDIRECT_URI), urlsplit(config.GMAIL_FRONTEND_URL)
    for uri in (callback, frontend):
        if uri.scheme != "http" or uri.hostname not in {"127.0.0.1", "localhost"} or uri.username or uri.password or uri.query or uri.fragment:
            raise HTTPException(503, "Gmail is restricted to the local owner workspace. Use the documented loopback URLs.")
    if callback.path != "/api/gmail/callback" or frontend.path not in {"", "/"} or callback.hostname != frontend.hostname:
        raise HTTPException(503, "Gmail callback and frontend must use the same loopback hostname and the implemented callback path.")
    return bool(config.GMAIL_CLIENT_ID and config.GMAIL_CLIENT_SECRET and config.GMAIL_TOKEN_ENCRYPTION_KEY)


class TokenVault:
    def __init__(self, root, key):
        self.path = Path(root) / "credentials.enc"
        try:
            self.cipher = Fernet(key.encode())
        except (ValueError, TypeError) as exc:
            raise HTTPException(503, "Generate a valid backend GMAIL_TOKEN_ENCRYPTION_KEY using the setup script.") from exc

    def load(self):
        if not self.path.exists():
            return None
        try:
            return json.loads(self.cipher.decrypt(self.path.read_bytes()))
        except (InvalidToken, ValueError, OSError) as exc:
            raise HTTPException(503, "The Gmail token store cannot be decrypted. Restore its original encryption key or disconnect and reconnect.") from exc

    def save(self, value):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        protect_local_path(self.path.parent, directory=True)
        temporary = self.path.with_suffix(".tmp")
        encrypted = self.cipher.encrypt(json.dumps(value).encode())
        with temporary.open("wb") as handle:
            handle.write(encrypted)
        protect_local_path(temporary)
        temporary.replace(self.path)
        protect_local_path(self.path)

    def delete(self):
        self.path.unlink(missing_ok=True)


class GmailManager:
    def __init__(self):
        self.lock = RLock()
        self.states = {}
        self.vault = None

    def ready(self):
        if not configuration():
            raise HTTPException(503, "Set GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET and GMAIL_TOKEN_ENCRYPTION_KEY in the backend .env, then restart.")
        if self.vault is None:
            self.vault = TokenVault(config.GMAIL_TOKEN_DIR, config.GMAIL_TOKEN_ENCRYPTION_KEY)

    def oauth_client(self, token=None):
        return OAuth2Client(config.GMAIL_CLIENT_ID, config.GMAIL_CLIENT_SECRET,
                            token_endpoint_auth_method="client_secret_post", scope=config.GMAIL_SCOPE,
                            redirect_uri=config.GMAIL_REDIRECT_URI, code_challenge_method="S256", token=token,
                            timeout=20, follow_redirects=False)

    def begin(self):
        self.ready()
        with self.lock:
            self.states = {k: v for k, v in self.states.items() if v["expires"] > time.time()}
            if len(self.states) >= 10:
                raise HTTPException(429, "Finish an existing connection attempt or wait ten minutes.")
            state, browser, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(32), secrets.token_urlsafe(64)
            self.states[state] = {"browser": browser, "verifier": verifier, "expires": time.time() + 600}
            with self.oauth_client() as oauth:
                url, _ = oauth.create_authorization_url(AUTH_URL, state=state, code_verifier=verifier,
                        access_type="offline", prompt="consent select_account", include_granted_scopes="false")
            return url, browser

    def finish(self, state, browser, code, error=None):
        self.ready()
        with self.lock:
            pending = self.states.get(state or "")
            if not pending or pending["expires"] <= time.time() or not browser or not secrets.compare_digest(browser, pending["browser"]):
                raise HTTPException(400, "Invalid, expired or wrong-browser OAuth state. Start Connect Gmail again.")
            self.states.pop(state)
            if error:
                return "denied"
            if not code:
                raise HTTPException(400, "Google did not return an authorization code.")
            try:
                with self.oauth_client() as oauth:
                    token = dict(oauth.fetch_token(TOKEN_URL, code=code, code_verifier=pending["verifier"]))
                if config.GMAIL_SCOPE not in token.get("scope", "").split() or not token.get("refresh_token") or not token.get("access_token"):
                    raise HTTPException(400, "Gmail read-only and offline access were not granted. Reconnect and approve that permission.")
                profile = self.api(token, "/profile")
                email = profile.get("emailAddress", "")
                if not email:
                    raise HTTPException(502, "Google did not identify the authorized mailbox.")
                self.vault.save({"email": email, "mailbox_key": hashlib.sha256(email.casefold().encode()).hexdigest(), "token": token})
                return "connected"
            except HTTPException:
                raise
            except Exception as exc:
                raise HTTPException(502, "Google authorization exchange failed. Try Connect Gmail again; no token values are exposed.") from exc

    def api(self, token, path, params=None):
        try:
            with HTTPClient(timeout=20, follow_redirects=False) as client:
                response = client.get(API_URL + path, headers={"Authorization": "Bearer " + token["access_token"]}, params=params)
            if response.status_code == 401:
                raise HTTPException(401, "Google access expired or was revoked. Reconnect Gmail.")
            if response.status_code in {403, 429}:
                raise HTTPException(503, "Gmail permission or quota prevents this request. Verify read-only access and retry later.")
            if response.status_code != 200:
                raise HTTPException(502, "Gmail API could not complete the request. Retry later.")
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(502, "Gmail API is temporarily unavailable. Retry later.") from exc

    def authorized(self):
        self.ready()
        stored = self.vault.load()
        if not stored:
            raise HTTPException(401, "Connect Gmail before syncing.")
        token = stored["token"]
        if float(token.get("expires_at", 0)) <= time.time() + 60:
            try:
                with self.oauth_client(token) as oauth:
                    renewed = dict(oauth.refresh_token(TOKEN_URL, refresh_token=token["refresh_token"]))
                renewed.setdefault("refresh_token", token["refresh_token"])
                stored["token"] = renewed
                self.vault.save(stored)
            except Exception as exc:
                raise HTTPException(401, "Google refresh authorization expired or was revoked. Reconnect Gmail.") from exc
        return stored

    def disconnect(self):
        with self.lock:
            self.states.clear()
            revoked = True
            token_path = config.GMAIL_TOKEN_DIR / "credentials.enc"
            try:
                if self.vault is None and token_path.exists():
                    self.vault = TokenVault(config.GMAIL_TOKEN_DIR, config.GMAIL_TOKEN_ENCRYPTION_KEY)
                if self.vault:
                    stored = self.vault.load()
                    if stored:
                        with HTTPClient(timeout=15, follow_redirects=False) as client:
                            response = client.post(REVOKE_URL, data={"token": stored["token"].get("refresh_token") or stored["token"]["access_token"]})
                        revoked = response.status_code == 200
            except Exception:
                revoked = False
            finally:
                token_path.unlink(missing_ok=True)
            return revoked
