"""Bounded, opaque-cookie synthetic sessions for one application process."""
import secrets
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock, RLock

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from .models import Base
from .seed import seed_demo

COOKIE_NAME = "moniq_demo"


@dataclass
class DemoSession:
    engine: object
    path: Path
    last_seen: float
    active: int = 0
    lock: Lock = field(default_factory=Lock)


class DemoSessionStore:
    def __init__(self, root, ttl_seconds=7200, maximum=100):
        if ttl_seconds < 1 or not 1 <= maximum <= 1000:
            raise ValueError("Demo sessions require a positive TTL and capacity between 1 and 1000.")
        root = Path(root)
        root.mkdir(parents=True, exist_ok=True)
        self.parent = root.resolve()
        self.directory = tempfile.TemporaryDirectory(prefix="instance-", dir=root)
        self.root = Path(self.directory.name)
        self.ttl = ttl_seconds
        self.maximum = maximum
        self.sessions = {}
        self.lock = RLock()

    def _prune(self):
        expired = [token for token, session in self.sessions.items()
                   if not session.active and time.monotonic() - session.last_seen >= self.ttl]
        for token in expired:
            session = self.sessions.pop(token)
            session.engine.dispose()
            session.path.unlink(missing_ok=True)

    def bootstrap(self, token=None):
        with self.lock:
            self._prune()
            if token in self.sessions:
                self.sessions[token].last_seen = time.monotonic()
                return token
            if len(self.sessions) >= self.maximum:
                raise HTTPException(503, "The demo is at capacity. Try again after a session expires.")
            token = secrets.token_hex(32)
            path = self.root / f"{token}.db"
            engine = create_engine(f"sqlite:///{path.as_posix()}", connect_args={"check_same_thread": False})
            try:
                Base.metadata.create_all(engine)
                with Session(engine) as db:
                    seed_demo(db)
            except Exception:
                engine.dispose()
                path.unlink(missing_ok=True)
                raise
            self.sessions[token] = DemoSession(engine, path, time.monotonic())
            return token

    @contextmanager
    def lease(self, token):
        with self.lock:
            self._prune()
            session = self.sessions.get(token)
            if session is None:
                raise HTTPException(401, "Your synthetic demo session expired. Reload Moniq to start a fresh session.")
            session.active += 1
            session.last_seen = time.monotonic()
        try:
            yield session
        finally:
            with self.lock:
                session.active -= 1
                session.last_seen = time.monotonic()

    def close(self):
        with self.lock:
            for session in self.sessions.values():
                session.engine.dispose()
            self.sessions.clear()
            if not self.root.resolve().is_relative_to(self.parent):
                raise ValueError("Session cleanup target escaped its owned directory.")
            self.directory.cleanup()
