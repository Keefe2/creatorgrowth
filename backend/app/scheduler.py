"""Due-post publishing, serverless-safe.

Instead of a background thread (which cannot exist on serverless platforms),
due posts are published opportunistically inside API requests, at most once
every 60 seconds per process. Local dev keeps working the same way.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from . import models
from .database import SessionLocal
from .publishers import get_publisher
from .security import decrypt_token

logger = logging.getLogger(__name__)

PUBLISH_INTERVAL_SECONDS = 60
_last_run: float = 0.0


def _utcnow() -> datetime:
    # Naive UTC: matches what SQLite/Postgres return for stored datetimes.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def publish_due_posts(db=None) -> int:
    """Publish every post whose scheduled_at has passed. Returns count published."""
    own_session = db is None
    if own_session:
        db = SessionLocal()
    published = 0
    try:
        now = _utcnow()
        due = (
            db.query(models.ContentPost)
            .filter(
                models.ContentPost.status == models.PostStatus.SCHEDULED,
                models.ContentPost.scheduled_at <= now,
            )
            .all()
        )
        for post in due:
            platforms = [p.strip() for p in post.platforms.split(",") if p.strip()]
            ok_all = True
            errors: list[str] = []
            for platform in platforms:
                account = (
                    db.query(models.SocialAccount)
                    .filter(
                        models.SocialAccount.user_id == post.user_id,
                        models.SocialAccount.platform == platform,
                    )
                    .first()
                )
                if account is None:
                    ok_all = False
                    errors.append(f"{platform}: no connected account")
                    continue
                try:
                    _ = decrypt_token(account.encrypted_token)  # credential check
                    result = get_publisher(platform).publish(account.account_name, post.title, post.body)
                except Exception as exc:  # never let one platform kill the batch
                    logger.exception("Publish failed for post %s on %s", post.id, platform)
                    ok_all = False
                    errors.append(f"{platform}: {exc}")
                    continue
                if not result.ok:
                    ok_all = False
                    errors.append(f"{platform}: {result.error}")
            if ok_all:
                post.status = models.PostStatus.PUBLISHED
                post.published_at = now
                published += 1
            else:
                post.status = models.PostStatus.FAILED
                post.error = "; ".join(errors)[:1000]
        db.commit()
    finally:
        if own_session:
            db.close()
    return published


def maybe_publish_due() -> None:
    """Run publish_due_posts() at most once per PUBLISH_INTERVAL_SECONDS."""
    global _last_run
    now = time.time()
    if now - _last_run < PUBLISH_INTERVAL_SECONDS:
        return
    _last_run = now
    try:
        publish_due_posts()
    except Exception:
        logger.exception("Opportunistic auto-publish failed")
