from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app import config, finance, main, notifications, seed
from backend.app.database import get_db
from backend.app.ml import Classifier


@pytest.fixture(scope="session")
def ml(tmp_path_factory):
    return Classifier(tmp_path_factory.mktemp("models"))


@pytest.fixture
def client(tmp_path, monkeypatch, ml):
    engine = create_engine(f"sqlite:///{(tmp_path / 'test.db').as_posix()}", connect_args={"check_same_thread": False})
    monkeypatch.setattr(main, "engine", engine)
    monkeypatch.setattr(main, "Classifier", lambda: ml)
    for module in (config, finance, seed, notifications):
        monkeypatch.setattr(module, "today", lambda: date(2026, 10, 9))

    def db_override():
        with Session(engine) as session:
            yield session

    main.app.dependency_overrides[get_db] = db_override
    with TestClient(main.app) as client:
        yield client
    main.app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture
def empty_client(client):
    assert client.delete("/api/data").status_code == 204
    return client
