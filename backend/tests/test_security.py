"""Security posture tests: headers, password hashing, token encryption, CORS."""


def test_security_headers_present(client):
    r = client.get("/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in r.headers["Content-Security-Policy"]
    assert r.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_password_not_stored_plaintext(db_session, client, user_token):
    from app import models
    from app.security import verify_password

    user = db_session.query(models.User).filter_by(email="test@example.com").first()
    assert user is not None
    assert user.password_hash != "StrongPass123!"
    assert user.password_hash.startswith("$2b$")
    assert verify_password("StrongPass123!", user.password_hash)
    assert not verify_password("WrongPass123!", user.password_hash)


def test_token_encryption_roundtrip():
    from app.security import decrypt_token, encrypt_token

    ct = encrypt_token("super-secret-token")
    assert ct != "super-secret-token"
    assert decrypt_token(ct) == "super-secret-token"


def test_cors_allows_configured_origin(client):
    r = client.options(
        "/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert r.status_code == 200
    assert "http://localhost:5173" in r.headers.get("access-control-allow-origin", "")


def test_sql_injection_attempt_is_harmless(client):
    r = client.post(
        "/auth/login",
        json={"email": "' OR '1'='1", "password": "x"},
    )
    # Invalid email format -> 422, no DB error leakage.
    assert r.status_code in (401, 422)
    assert "sqlite" not in r.text.lower() and "sql" not in r.text.lower()


def test_register_existing_email_is_enumeration_safe(client, db_session, fixed_otp):
    """Re-registering an existing email must return the SAME 201 response — no 409 oracle."""
    from app import models

    r1 = client.post(
        "/auth/register",
        json={"email": "enum@example.com", "name": "Enum", "password": "StrongPass123!"},
    )
    assert r1.status_code == 201
    r2 = client.post(
        "/auth/register",
        json={"email": "enum@example.com", "name": "Attacker", "password": "OtherPass123!"},
    )
    assert r2.status_code == 201, r2.text
    assert r2.json()["message"] == r1.json()["message"]
    # No duplicate user, original password untouched.
    users = db_session.query(models.User).filter_by(email="enum@example.com").all()
    assert len(users) == 1
    assert users[0].name == "Enum"

    # Same for an already-verified user: still 201, still generic.
    client.post("/auth/verify-otp", json={"email": "enum@example.com", "otp": fixed_otp})
    r3 = client.post(
        "/auth/register",
        json={"email": "enum@example.com", "name": "Attacker", "password": "OtherPass123!"},
    )
    assert r3.status_code == 201
    assert r3.json()["message"] == r1.json()["message"]


def test_refresh_token_reuse_revokes_whole_family(client, fixed_otp):
    """Reusing a revoked refresh token nukes the token family (theft detection)."""
    client.post(
        "/auth/register",
        json={"email": "reuse@example.com", "name": "Reuse", "password": "StrongPass123!"},
    )
    login = client.post(
        "/auth/login", json={"email": "reuse@example.com", "password": "StrongPass123!"}
    )
    # verify first (login requires verified)
    client.post("/auth/verify-otp", json={"email": "reuse@example.com", "otp": fixed_otp})
    login = client.post(
        "/auth/login", json={"email": "reuse@example.com", "password": "StrongPass123!"}
    )
    rt1 = login.json()["refresh_token"]
    r2 = client.post("/auth/refresh", json={"refresh_token": rt1})
    assert r2.status_code == 200
    rt2 = r2.json()["refresh_token"]
    # Attacker replays the stolen rt1 -> 401 AND the whole family dies.
    assert client.post("/auth/refresh", json={"refresh_token": rt1}).status_code == 401
    # Even the legitimately rotated rt2 is now dead.
    assert client.post("/auth/refresh", json={"refresh_token": rt2}).status_code == 401


def test_db_rate_limit_blocks_login_bruteforce(client, monkeypatch):
    """DB-backed rate limit must 429 brute force even when slowapi is permissive."""
    from app.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "rl_login_ip_per_minute", 2)
    statuses = [
        client.post(
            "/auth/login", json={"email": "brute@example.com", "password": "WrongPass123!"}
        ).status_code
        for _ in range(4)
    ]
    assert statuses[0] == 401
    assert statuses[1] == 401
    assert statuses[2] == 429
    assert statuses[3] == 429


def test_get_client_ip_prefers_forwarded_for():
    from unittest.mock import MagicMock

    from app.rate_limit_db import get_client_ip

    req = MagicMock()
    req.headers = {"x-forwarded-for": "1.2.3.4, 5.6.7.8"}
    req.client.host = "9.9.9.9"
    # Last entry is the one Vercel's edge appended -> trustworthy.
    assert get_client_ip(req) == "5.6.7.8"
