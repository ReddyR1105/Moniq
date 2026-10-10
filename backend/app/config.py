import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
RUNTIME = ROOT / ".runtime"
RUNTIME.mkdir(exist_ok=True)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{(RUNTIME / 'moniq.db').as_posix()}")
MODEL_DIR = Path(os.getenv("MODEL_DIR", str(RUNTIME / "models")))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173").split(",")
PUBLIC_DEMO = os.getenv("MONIQ_PUBLIC_DEMO", "false").lower() == "true"
SERVE_FRONTEND = os.getenv("MONIQ_SERVE_FRONTEND", str(PUBLIC_DEMO)).lower() == "true"
COOKIE_SECURE = os.getenv("MONIQ_COOKIE_SECURE", "true").lower() == "true"
PUBLIC_ORIGIN = os.getenv("MONIQ_PUBLIC_ORIGIN", os.getenv("RENDER_EXTERNAL_URL", "")).rstrip("/")
PUBLIC_MODEL_DIR = RUNTIME / "public-models"
SESSION_TTL_SECONDS = int(os.getenv("MONIQ_SESSION_TTL_SECONDS", "7200"))
MAX_DEMO_SESSIONS = int(os.getenv("MONIQ_MAX_DEMO_SESSIONS", "100"))


def today():
    return datetime.now(ZoneInfo("America/New_York")).date()
