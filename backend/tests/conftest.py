"""Test fixtures: isolated in-memory SQLite + TestClient."""
import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["TESTING"] = "1"
os.environ["REGISTER_RATE_LIMIT"] = "1000/hour"
os.environ["LOGIN_RATE_LIMIT"] = "1000/minute"
os.environ["JWT_SECRET"] = "test-secret-" + "x" * 40
os.environ["ENCRYPTION_KEY"] = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
os.environ["CORS_ORIGINS"] = "http://localhost:5173"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.database import Base, get_db
from app.main import app
from app.routers import auth as auth_router


@pytest.fixture()
def fixed_otp(monkeypatch):
    """Pin OTP generation to a known code so tests can verify."""
    monkeypatch.setattr(auth_router, "_generate_otp_code", lambda: "123456")
    return "123456"


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = Session()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture()
def client(db_session):
    def _override():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def user_token(client, fixed_otp):
    """A fully verified user: register -> verify OTP -> token pair."""
    r = client.post(
        "/auth/register",
        json={"email": "test@example.com", "name": "Tester", "password": "StrongPass123!"},
    )
    assert r.status_code == 201, r.text
    v = client.post("/auth/verify-otp", json={"email": "test@example.com", "otp": fixed_otp})
    assert v.status_code == 200, v.text
    data = v.json()
    return data["access_token"], data["refresh_token"]


@pytest.fixture()
def auth_headers(user_token):
    access, _ = user_token
    return {"Authorization": f"Bearer {access}"}
