"""Background scheduler: publishes due scheduled posts every 60 seconds."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from . import models
from .database import SessionLocal
from .publishers import get_publisher
from .security import decrypt_token

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    # Naive UTC: matches what SQLite returns for stored datetimes.
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


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(publish_due_posts, "interval", seconds=60, id="publish_due_posts", max_instances=1)
    scheduler.start()
    return scheduler
