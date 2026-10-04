"""Auth flow tests: register, login, refresh rotation, logout, guards."""


def test_register_and_me(client, user_token, auth_headers):
    r = client.get("/auth/me", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["email"] == "test@example.com"


def test_register_duplicate_email(client, user_token):
    r = client.post(
        "/auth/register",
        json={"email": "test@example.com", "name": "Dup", "password": "StrongPass123!"},
    )
    assert r.status_code == 409


def test_register_weak_password_rejected(client):
    r = client.post(
        "/auth/register",
        json={"email": "weak@example.com", "name": "Weak", "password": "short"},
    )
    assert r.status_code == 422


def test_login_wrong_password(client, user_token):
    r = client.post("/auth/login", json={"email": "test@example.com", "password": "WrongPass123!"})
    assert r.status_code == 401


def test_refresh_rotation(client, user_token):
    _, refresh = user_token
    r1 = client.post("/auth/refresh", json={"refresh_token": refresh})
    assert r1.status_code == 200
    new_refresh = r1.json()["refresh_token"]
    # Old refresh token must now be dead (rotation).
    r2 = client.post("/auth/refresh", json={"refresh_token": refresh})
    assert r2.status_code == 401
    # New one works.
    r3 = client.post("/auth/refresh", json={"refresh_token": new_refresh})
    assert r3.status_code == 200


def test_logout_revokes(client, user_token):
    _, refresh = user_token
    r = client.post("/auth/logout", json={"refresh_token": refresh})
    assert r.status_code == 204
    r2 = client.post("/auth/refresh", json={"refresh_token": refresh})
    assert r2.status_code == 401


def test_protected_without_token(client):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/content").status_code == 401


def test_tampered_token_rejected(client, auth_headers):
    bad = {"Authorization": auth_headers["Authorization"] + "tampered"}
    assert client.get("/auth/me", headers=bad).status_code == 401
