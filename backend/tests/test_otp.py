"""Email OTP verification tests: register gate, verify, resend, lockout, happy path."""
from datetime import datetime, timedelta, timezone

from app import models


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _register(client, email="otp@example.com"):
    r = client.post(
        "/auth/register",
        json={"email": email, "name": "OTP User", "password": "StrongPass123!"},
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_register_returns_201_with_otp_required_and_no_tokens(client, fixed_otp):
    data = _register(client)
    assert data["otp_required"] is True
    # Generic message (identical for new and existing emails — no enumeration).
    assert data["message"] == "Check your email for next steps."
    assert data["user"]["email"] == "otp@example.com"
    assert "access_token" not in data
    assert "refresh_token" not in data


def test_login_before_verification_is_forbidden(client, fixed_otp):
    _register(client)
    r = client.post("/auth/login", json={"email": "otp@example.com", "password": "StrongPass123!"})
    assert r.status_code == 403
    assert r.json()["detail"] == "email_not_verified"


def test_verify_wrong_code_400_and_attempts_increment(client, db_session, fixed_otp):
    _register(client)
    r = client.post("/auth/verify-otp", json={"email": "otp@example.com", "otp": "000000"})
    assert r.status_code == 400
    assert r.json()["detail"] == "Invalid code"
    record = db_session.query(models.EmailOTP).one()
    assert record.attempts == 1
    assert record.consumed is False


def test_verify_correct_code_issues_tokens(client, db_session, fixed_otp):
    _register(client)
    r = client.post("/auth/verify-otp", json={"email": "otp@example.com", "otp": fixed_otp})
    assert r.status_code == 200
    data = r.json()
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["user"]["email"] == "otp@example.com"
    user = db_session.query(models.User).filter_by(email="otp@example.com").one()
    assert user.is_verified is True
    record = db_session.query(models.EmailOTP).one()
    assert record.consumed is True


def test_verify_expired_otp_rejected(client, db_session, fixed_otp):
    _register(client)
    record = db_session.query(models.EmailOTP).one()
    record.expires_at = _utcnow() - timedelta(minutes=1)
    db_session.commit()
    r = client.post("/auth/verify-otp", json={"email": "otp@example.com", "otp": fixed_otp})
    assert r.status_code == 400
    assert r.json()["detail"] == "Invalid or expired code"


def test_verify_max_attempts_locks_code(client, fixed_otp):
    _register(client)
    for _ in range(5):  # otp_max_attempts default
        r = client.post("/auth/verify-otp", json={"email": "otp@example.com", "otp": "000000"})
        assert r.status_code == 400
    # Even the correct code is now rejected until a fresh code is requested.
    r = client.post("/auth/verify-otp", json={"email": "otp@example.com", "otp": fixed_otp})
    assert r.status_code == 400
    assert "Too many attempts" in r.json()["detail"]


def test_verify_unknown_email_rejected(client):
    r = client.post("/auth/verify-otp", json={"email": "ghost@example.com", "otp": "123456"})
    assert r.status_code == 400
    assert r.json()["detail"] == "Invalid or expired code"


def test_verify_bad_otp_format_rejected(client, fixed_otp):
    _register(client)
    r = client.post("/auth/verify-otp", json={"email": "otp@example.com", "otp": "abc"})
    assert r.status_code == 422


def test_resend_cooldown_then_success(client, db_session, fixed_otp):
    _register(client)
    # Immediate resend hits the cooldown.
    r = client.post("/auth/resend-otp", json={"email": "otp@example.com"})
    assert r.status_code == 429
    # Backdate past the cooldown window.
    record = db_session.query(models.EmailOTP).one()
    record.created_at = _utcnow() - timedelta(seconds=120)
    db_session.commit()
    r = client.post("/auth/resend-otp", json={"email": "otp@example.com"})
    assert r.status_code == 200
    assert r.json()["otp_required"] is True
    # Old code consumed, exactly one fresh unconsumed code exists.
    records = db_session.query(models.EmailOTP).order_by(models.EmailOTP.id).all()
    assert len(records) == 2
    assert records[0].consumed is True
    assert records[1].consumed is False


def test_resend_unknown_email_returns_generic_success(client):
    r = client.post("/auth/resend-otp", json={"email": "nobody@example.com"})
    assert r.status_code == 200
    assert r.json()["otp_required"] is True


def test_resend_after_verified_says_already_verified(client, db_session, fixed_otp):
    _register(client)
    r = client.post("/auth/verify-otp", json={"email": "otp@example.com", "otp": fixed_otp})
    assert r.status_code == 200
    r = client.post("/auth/resend-otp", json={"email": "otp@example.com"})
    assert r.status_code == 200
    assert r.json()["otp_required"] is False


def test_full_happy_path_register_verify_login(client, fixed_otp):
    _register(client, email="happy@example.com")
    v = client.post("/auth/verify-otp", json={"email": "happy@example.com", "otp": fixed_otp})
    assert v.status_code == 200
    r = client.post("/auth/login", json={"email": "happy@example.com", "password": "StrongPass123!"})
    assert r.status_code == 200
    assert r.json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == "happy@example.com"


def test_otp_never_stored_in_plaintext(client, db_session, fixed_otp):
    _register(client)
    record = db_session.query(models.EmailOTP).one()
    assert record.otp_hash != fixed_otp
    assert len(record.otp_hash) == 64  # SHA256 hex


def test_as_naive_utc_handles_postgres_aware_datetimes():
    """Regression: Postgres timestamptz columns come back tz-aware; the
    codebase compares naive UTC. _as_naive_utc must normalize both."""
    from datetime import timezone as tz
    from app.routers.auth import _as_naive_utc, _utcnow

    aware = datetime.now(tz.utc)
    naive = _as_naive_utc(aware)
    assert naive.tzinfo is None
    # Same instant, comparisons must not raise and must be correct.
    assert naive <= _utcnow() + timedelta(seconds=5)
    assert naive >= _utcnow() - timedelta(seconds=5)
    # Naive input passes through untouched.
    plain = datetime(2026, 1, 1, 12, 0, 0)
    assert _as_naive_utc(plain) == plain
    # Non-UTC aware input converts to UTC first.
    plus5 = datetime(2026, 1, 1, 17, 0, 0, tzinfo=tz(timedelta(hours=5)))
    assert _as_naive_utc(plus5) == datetime(2026, 1, 1, 12, 0, 0)
