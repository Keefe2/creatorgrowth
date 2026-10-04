"""Content studio + scheduling + accounts + analytics + comments tests."""
from datetime import datetime, timedelta, timezone


def test_ai_generate(client, auth_headers):
    r = client.post(
        "/content/generate",
        headers=auth_headers,
        json={"topic": "Subah ki walk", "tone": "viral", "platform": "facebook", "language": "ur"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["title"] and data["body"] and data["hashtags"]


def test_create_and_list_draft(client, auth_headers):
    r = client.post(
        "/content",
        headers=auth_headers,
        json={"title": "T", "body": "Hello world", "platforms": ["facebook", "x"]},
    )
    assert r.status_code == 201, r.text
    post = r.json()
    assert post["status"] == "draft"
    assert set(post["platforms"]) == {"facebook", "x"}

    r2 = client.get("/content", headers=auth_headers)
    assert r2.status_code == 200
    assert len(r2.json()) == 1


def test_schedule_in_past_rejected(client, auth_headers):
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    r = client.post(
        "/content/schedule",
        headers=auth_headers,
        json={"title": "T", "body": "B", "platforms": ["facebook"], "scheduled_at": past},
    )
    assert r.status_code == 422


def test_schedule_future_and_due_publish(client, auth_headers, db_session):
    future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    r = client.post(
        "/content/schedule",
        headers=auth_headers,
        json={"title": "T", "body": "B", "platforms": ["facebook"], "scheduled_at": future},
    )
    assert r.status_code == 201
    assert r.json()["status"] == "scheduled"

    # Simulate the background worker picking up a due post.
    from app import models
    from app.scheduler import publish_due_posts

    post = db_session.query(models.ContentPost).first()
    post.scheduled_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()
    # No connected account -> should fail cleanly, not crash.
    n = publish_due_posts(db_session)
    assert n == 0
    db_session.refresh(post)
    assert post.status == models.PostStatus.FAILED
    assert "no connected account" in post.error


def test_delete_other_users_post_forbidden(client, auth_headers, db_session):
    # Create a second user and post directly.
    from app import models
    from app.security import hash_password

    other = models.User(email="other@example.com", name="O", password_hash=hash_password("StrongPass123!"))
    db_session.add(other)
    db_session.commit()
    post = models.ContentPost(user_id=other.id, title="X", body="Y", platforms="facebook")
    db_session.add(post)
    db_session.commit()

    r = client.delete(f"/content/{post.id}", headers=auth_headers)
    assert r.status_code == 404  # not visible across users


def test_accounts_encrypted_and_hidden(client, auth_headers):
    r = client.post(
        "/accounts",
        headers=auth_headers,
        json={"platform": "facebook", "account_name": "MyPage", "access_token": "sekret-token-123"},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert "access_token" not in data
    assert "encrypted_token" not in data

    r2 = client.post(f"/accounts/{data['id']}/verify", headers=auth_headers)
    assert r2.status_code == 200
    assert r2.json()["ok"] is True


def test_analytics_dashboard(client, auth_headers):
    client.post(
        "/analytics/snapshot",
        headers=auth_headers,
        json={"platform": "facebook", "followers": 100, "impressions": 5000, "engagement": 300},
    )
    r = client.get("/analytics/dashboard", headers=auth_headers)
    assert r.status_code == 200
    d = r.json()
    assert d["totals"]["followers"] == 100
    assert d["totals"]["impressions"] == 5000


def test_comment_queue(client, auth_headers):
    r = client.post(
        "/comments/queue",
        headers=auth_headers,
        json={"platform": "x", "post_ref": "12345", "comment_text": "Nice!"},
    )
    assert r.status_code == 201
    task_id = r.json()["id"]
    r2 = client.post(f"/comments/queue/{task_id}/done", headers=auth_headers)
    assert r2.status_code == 200
