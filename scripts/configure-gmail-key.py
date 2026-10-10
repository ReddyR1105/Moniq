"""Write an encryption key locally; never print it or replace an existing key."""
import sys
from pathlib import Path

from cryptography.fernet import Fernet
from dotenv import dotenv_values

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from backend.app.local_secrets import protect_local_path  # noqa: E402

env_path = root / ".env"
if not env_path.exists():
    env_path.write_bytes((root / ".env.example").read_bytes())
values = dotenv_values(env_path)
if values.get("GMAIL_TOKEN_ENCRYPTION_KEY"):
    Fernet(values["GMAIL_TOKEN_ENCRYPTION_KEY"].encode())
    protect_local_path(env_path)
    print("Existing Gmail encryption key retained in .env. Keep a private backup of that file.")
else:
    lines = env_path.read_text(encoding="utf-8").splitlines()
    setting = "GMAIL_TOKEN_ENCRYPTION_KEY=" + Fernet.generate_key().decode()
    matches = [i for i, line in enumerate(lines) if line.startswith("GMAIL_TOKEN_ENCRYPTION_KEY=")]
    if matches:
        lines[matches[0]] = setting
    else:
        lines.append(setting)
    env_path.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
    protect_local_path(env_path)
    print("Gmail encryption key written to local .env without displaying it. Add the OAuth ID and secret there, then restart Moniq.")
