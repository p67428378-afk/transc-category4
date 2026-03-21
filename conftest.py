import pytest
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set dummy environment variables for testing before importing app components
os.environ["SECRET_KEY"] = "super-secret-test-key"
os.environ["ALGORITHM"] = "HS256"
os.environ["DATABASE_URL"] = "sqlite:///./test.db" # This will be overridden by StaticPool anyway

from backend.dependencies import get_db
from backend.database import Base
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
