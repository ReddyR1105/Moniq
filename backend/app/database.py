from fastapi import HTTPException, Request
from threading import RLock
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from . import config
from .config import DATABASE_URL
from .models import Account, Base, Profile

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
_personal_lock = RLock()


def personal_engine(app):
    if app.state.public_demo or getattr(app.state, "hosted_app", False):
        raise HTTPException(403, "Private databases are unavailable in public demo mode.")
    with _personal_lock:
        if getattr(app.state, "personal_engine", None) is None:
            owned = create_engine(config.PERSONAL_DATABASE_URL, connect_args={"check_same_thread": False})
            Base.metadata.create_all(owned)
            with Session(owned) as db:
                if not db.get(Profile, 1) and not db.scalar(select(Account.id)):
                    db.add(Profile(id=1, name="Student", university="Not set", allowance_cents=0,
                                   income_preference="Mixed income", student_verified=False))
                    db.commit()
            app.state.personal_engine = owned
    return app.state.personal_engine


def get_personal_db(request: Request):
    if getattr(request.app.state, "hosted_app", False):
        if not hasattr(request.state, "private_engine"):
            raise HTTPException(403, "Authenticate in your private workspace first.")
        yield from get_db(request)
        return
    with Session(personal_engine(request.app), expire_on_commit=False) as db:
        yield db


def get_db(request: Request):
    if hasattr(request.state, "private_engine"):
        session = Session(request.state.private_engine, expire_on_commit=False)
        if session.bind.dialect.name == "postgresql" and request.method in {"POST", "PUT", "DELETE"}:
            session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:owner))"), {"owner": request.state.identity.user_id})
    elif hasattr(request.state, "demo_engine"):
        session = Session(request.state.demo_engine, expire_on_commit=False)
    elif request.app.state.public_demo or getattr(request.app.state, "hosted_app", False):
        raise HTTPException(401, "Start your isolated synthetic session first.")
    elif request.cookies.get("moniq_workspace") == "personal":
        session = Session(personal_engine(request.app), expire_on_commit=False)
    elif request.cookies.get("moniq_workspace") == "scenario":
        session = Session(scenario_engine(request.app), expire_on_commit=False)
    else:
        session = SessionLocal()
    with session:
        yield session


def scenario_engine(app):
    if app.state.public_demo or getattr(app.state, "hosted_app", False):
        raise HTTPException(403, "Owner scenario databases are unavailable in public demo mode.")
    with _personal_lock:
        if getattr(app.state, "scenario_engine", None) is None:
            owned = create_engine(config.SCENARIO_DATABASE_URL, connect_args={"check_same_thread": False})
            Base.metadata.create_all(owned)
            app.state.scenario_engine = owned
    return app.state.scenario_engine
