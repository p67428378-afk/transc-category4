"""Auto-generated conftest.py for FastAPI + SQLAlchemy testing.
Uses StaticPool to share a single in-memory SQLite connection across all threads.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Manual Fixes:
from backend.database import Base, get_db
from backend.main import app

# Single engine for ALL test fixtures — StaticPool ensures one shared connection
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Yields a clean database session for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Yields a TestClient that shares the SAME engine as db_session."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass  # db_session cleanup handled by the db_session fixture

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
