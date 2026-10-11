"""Local HTTPS browser fixture. Uses only synthetic identities and isolated files."""
import os
from pathlib import Path
import secrets
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if os.getenv("MONIQ_SYNTHETIC_TEST_SERVER") != "1":
    raise SystemExit("This fixture requires MONIQ_SYNTHETIC_TEST_SERVER=1 and must never be deployed.")
os.environ.update(MONIQ_PUBLIC_DEMO="true", MONIQ_GMAIL_DISABLED="true", MONIQ_SERVE_FRONTEND="true", MONIQ_HOSTED_APP="true",
                  MONIQ_PRIVATE_ACCOUNTS_ENABLED="false", DATABASE_URL="sqlite://", GMAIL_CLIENT_ID="", GMAIL_CLIENT_SECRET="", GMAIL_TOKEN_ENCRYPTION_KEY="")

from datetime import datetime, timedelta, timezone  # noqa: E402
import ipaddress  # noqa: E402
from cryptography import x509  # noqa: E402
from cryptography.hazmat.primitives import hashes, serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import rsa  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from backend.app import main  # noqa: E402
from backend.app.hosted_settings import HostedSettings  # noqa: E402
from backend.app.identity import IdentityStore  # noqa: E402
import uvicorn  # noqa: E402
import asyncio  # noqa: E402

directory = ROOT / ".runtime" / "hosted-browser"
directory.mkdir(parents=True, exist_ok=True)
settings = HostedSettings(enabled=True, private_enabled=True, origin="https://127.0.0.1:8005",
                          session_key=secrets.token_urlsafe(48), allowed_emails=("student@moniq.example.test", "invited@moniq.example.test"))


class SyntheticMailer:
    def send(self, *args):
        pass


store = IdentityStore(settings, test_engine=create_engine("sqlite:///" + (directory / (secrets.token_hex(8) + ".db")).as_posix(), connect_args={"check_same_thread": False}), mailer=SyntheticMailer())
# Synthetic invitation is redeemed in the fixture; never exposes a real email or password.
from backend.app.identity import PASSWORDS  # noqa: E402
from backend.app.identity_models import EmailGrant, User  # noqa: E402
from backend.app.identity import digest  # noqa: E402
import time  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402
import uuid  # noqa: E402
with Session(store.engine) as db:
    user_id = uuid.uuid4().hex
    store.workspace(user_id)
    db.add(User(id=user_id, email=settings.allowed_emails[0], password_hash=PASSWORDS.hash("synthetic student password 123"), verified=True, enabled=True))
    db.add(EmailGrant(digest=digest("synthetic-invitation-code-123"), email=settings.allowed_emails[1], purpose="invite", expires=int(time.time())+3600))
    db.commit()
# Patch only this dedicated local test process; no application environment bypass exists.
HostedSettings.load = classmethod(lambda cls: settings)
HostedSettings.validate = lambda self: None
main.IdentityStore = lambda _: store

key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
subject = x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, "Moniq synthetic localhost test")])
certificate = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key())
               .serial_number(x509.random_serial_number()).not_valid_before(datetime.now(timezone.utc) - timedelta(minutes=1))
               .not_valid_after(datetime.now(timezone.utc) + timedelta(days=2))
               .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]), critical=False)
               .sign(key, hashes.SHA256()))
cert_file, key_file = directory / "localhost.crt", directory / "localhost.key"
cert_file.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
key_file.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
server = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=8005, ssl_keyfile=str(key_file), ssl_certfile=str(cert_file), access_log=False))
# The Windows Proactor loop reports reset errors when test browsers close TLS probes.
# A selector loop is sufficient for this single-process localhost fixture.
with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
    runner.run(server.serve())
