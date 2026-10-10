from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db(request: Request):
    factory = (lambda: Session(request.state.demo_engine, expire_on_commit=False)) if hasattr(request.state, "demo_engine") else SessionLocal
    with factory() as session:
        yield session
