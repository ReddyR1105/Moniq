"""Independent hosted settings. Legacy local Gmail secrets are never reused."""
import os
from dataclasses import dataclass
from urllib.parse import urlsplit

from cryptography.fernet import Fernet


def flag(name):
    return os.getenv(name, "false").lower() == "true"


@dataclass(frozen=True)
class HostedSettings:
    enabled: bool = False
    private_enabled: bool = False
    origin: str = ""
    database_url: str = ""
    session_key: str = ""
    allowed_emails: tuple[str, ...] = ()
    persistence_verified: bool = False
    recovery_verified: bool = False
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""
    mail_from: str = ""
    mail_transport: str = "smtp"
    mail_api_key: str = ""
    gmail_enabled: bool = False
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    gmail_key: str = ""

    @property
    def redirect_uri(self):
        return self.origin + "/api/gmail/callback"

    @classmethod
    def load(cls):
        enabled = flag("MONIQ_HOSTED_APP")
        private = enabled and flag("MONIQ_PRIVATE_ACCOUNTS_ENABLED")
        gmail = private and flag("MONIQ_HOSTED_GMAIL_ENABLED")
        return cls(enabled=enabled, private_enabled=private,
                   origin=os.getenv("MONIQ_PUBLIC_ORIGIN", os.getenv("RENDER_EXTERNAL_URL", "")).rstrip("/"),
                   database_url=os.getenv("HOSTED_DATABASE_URL", "") if private else "",
                   session_key=os.getenv("MONIQ_SESSION_SIGNING_KEY", "") if private else "",
                   allowed_emails=tuple(e.strip().casefold() for e in os.getenv("MONIQ_TEST_USER_EMAILS", "").split(",") if e.strip()) if private else (),
                   persistence_verified=flag("MONIQ_PERSISTENCE_VERIFIED"), recovery_verified=flag("MONIQ_RECOVERY_VERIFIED"),
                   smtp_host=os.getenv("MONIQ_SMTP_HOST", "") if private else "",
                   smtp_port=int(os.getenv("MONIQ_SMTP_PORT", "465")),
                   smtp_user=os.getenv("MONIQ_SMTP_USER", "") if private else "",
                   smtp_password=os.getenv("MONIQ_SMTP_PASSWORD", "") if private else "",
                   mail_from=os.getenv("MONIQ_MAIL_FROM", "") if private else "",
                   mail_transport=os.getenv("MONIQ_MAIL_TRANSPORT", "smtp"),
                   mail_api_key=os.getenv("MONIQ_MAIL_API_KEY", "") if private else "",
                   gmail_enabled=gmail,
                   gmail_client_id=os.getenv("HOSTED_GMAIL_CLIENT_ID", "") if gmail else "",
                   gmail_client_secret=os.getenv("HOSTED_GMAIL_CLIENT_SECRET", "") if gmail else "",
                   gmail_key=os.getenv("HOSTED_GMAIL_TOKEN_ENCRYPTION_KEY", "") if gmail else "")

    def validate(self):
        parsed = urlsplit(self.origin)
        if parsed.scheme != "https" or not parsed.hostname or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password:
            raise ValueError("Hosted Moniq requires a fixed HTTPS MONIQ_PUBLIC_ORIGIN.")
        if not self.private_enabled:
            return
        if not self.persistence_verified or not self.recovery_verified:
            raise ValueError("Private accounts require a verified restore/restart drill and verified email recovery.")
        if not self.database_url.startswith(("postgresql://", "postgres://", "postgresql+psycopg://")):
            raise ValueError("Private accounts require HOSTED_DATABASE_URL pointing to persistent PostgreSQL.")
        if len(self.session_key) < 43 or not self.allowed_emails:
            raise ValueError("Configure a random session signing key and an explicit test-user email allowlist.")
        if not self.mail_from or self.mail_transport not in {"smtp", "resend"}:
            raise ValueError("Configure a verified sender and supported backend mail transport.")
        if self.mail_transport == "smtp" and (not self.smtp_host or not self.smtp_user or not self.smtp_password or self.smtp_port not in {465, 587}):
            raise ValueError("Configure authenticated TLS email delivery for invitations and password recovery.")
        if self.mail_transport == "resend" and not self.mail_api_key:
            raise ValueError("Configure the backend-only HTTPS email provider key.")
        if self.gmail_enabled:
            if not self.gmail_client_id or not self.gmail_client_secret:
                raise ValueError("Configure backend-only hosted Gmail OAuth credentials.")
            try:
                Fernet(self.gmail_key.encode())
            except (ValueError, TypeError) as exc:
                raise ValueError("Hosted Gmail requires a stable valid encryption key.") from exc
