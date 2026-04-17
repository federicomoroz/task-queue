from unittest.mock import patch

import pytest
from fakeredis import FakeRedis
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sqlalchemy.pool import StaticPool

import app.core.database as _db_mod
import app.core.redis_client as _redis_mod
from app.core.database import Base
from app.core.event_manager import EventManager
from app.main import app
from app.controllers.tasks_controller import set_event_manager


@pytest.fixture()
def db_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture()
def fake_redis():
    client = FakeRedis(decode_responses=True)
    original = _redis_mod.get_redis
    _redis_mod.get_redis = lambda: client
    yield client
    _redis_mod.get_redis = original
    client.close()


@pytest.fixture()
def event_manager():
    return EventManager()


@pytest.fixture()
def test_client(db_engine, fake_redis):
    """
    TestClient with in-memory DB and fake Redis.
    Patches SessionLocal and create_tables so the lifespan uses the test DB.
    """
    test_session_factory = sessionmaker(bind=db_engine)

    original_session_local = _db_mod.SessionLocal
    original_engine = _db_mod.engine
    _db_mod.SessionLocal = test_session_factory
    _db_mod.engine = db_engine

    em = EventManager()
    set_event_manager(em)

    with TestClient(app, raise_server_exceptions=True) as client:
        yield client

    _db_mod.SessionLocal = original_session_local
    _db_mod.engine = original_engine
