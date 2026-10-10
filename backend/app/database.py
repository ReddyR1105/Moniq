from fastapi import Request
from threading import RLock
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from . import config
from .config import DATABASE_URL
from .models import Account, Base, Profile

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
_personal_lock = RLock()


def personal_engine(app):
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
    with Session(personal_engine(request.app), expire_on_commit=False) as db:
        yield db


def get_db(request: Request):
    if hasattr(request.state, "demo_engine"):
        session = Session(request.state.demo_engine, expire_on_commit=False)
    elif request.cookies.get("moniq_workspace") == "personal":
        session = Session(personal_engine(request.app), expire_on_commit=False)
    elif request.cookies.get("moniq_workspace") == "scenario":
        session = Session(scenario_engine(request.app), expire_on_commit=False)
    else:
        session = SessionLocal()
    with session:
        yield session


def scenario_engine(app):
    with _personal_lock:
        if getattr(app.state, "scenario_engine", None) is None:
            owned = create_engine(config.SCENARIO_DATABASE_URL, connect_args={"check_same_thread": False})
            Base.metadata.create_all(owned)
            app.state.scenario_engine = owned
    return app.state.scenario_engine
