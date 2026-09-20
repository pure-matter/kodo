from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.seed import seed_all


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    """A TestClient backed by its own in-memory db, pre-seeded with
    categories/rules/allocations, for exercising the API end to end.

    Uses StaticPool (one shared connection) rather than db_session's engine,
    because TestClient runs the app in a separate thread and raw sqlite3
    connections can't cross threads.

    Deliberately NOT used as a context manager (`with TestClient(app)`):
    that would trigger app.main's lifespan, which runs real Alembic
    migrations and seeding against the actual kodo.db file via SessionLocal
    - bypassing this fixture's get_db override entirely, since lifespan
    isn't part of the dependency-injection system. This fixture already
    does its own create_all + seed against the in-memory db, so the app's
    startup routine is neither needed nor safe to run here.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)

    with TestingSession() as db:
        seed_all(db)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()
