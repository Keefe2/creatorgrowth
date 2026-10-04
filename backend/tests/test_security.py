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
