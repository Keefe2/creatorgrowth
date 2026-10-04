"""Serverless-safe rate limiting backed by the database.

slowapi keeps its counters in process memory, which does not survive across
serverless function instances — on Vercel, brute-force protection was
effectively absent (verified live: 8 rapid bad logins, zero 429s). These
counters live in Postgres/SQLite, so they work across every instance.
"""
from datetime import datetime, timedelta, timezone

from fastapi import Request
from sqlalchemy.orm import Session

from . import models


def _utcnow() -> datetime:
    # Naive UTC everywhere: SQLite does not preserve tzinfo.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_client_ip(request: Request) -> str:
    """Best-effort real client IP behind proxies.

    On Vercel's edge the genuine client IP is appended LAST to
    X-Forwarded-For (earlier entries can be spoofed by the client), so the
    last entry is the trustworthy one.
    """
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        if parts:
            return parts[-1][:64]
    if request.client and request.client.host:
        return request.client.host[:64]
    return "unknown"


def rate_limit_ok(db: Session, key: str, max_hits: int, window_seconds: int) -> bool:
    """Fixed-window rate limit. Returns True if the hit is allowed (and records it)."""
    now = _utcnow()
    cutoff = now - timedelta(seconds=window_seconds)
    # Prune expired hits for this key, plus anything older than 24h (hygiene).
    db.query(models.RateLimitHit).filter(
        models.RateLimitHit.key == key,
        models.RateLimitHit.created_at < cutoff,
    ).delete(synchronize_session=False)
    db.query(models.RateLimitHit).filter(
        models.RateLimitHit.created_at < now - timedelta(hours=24)
    ).delete(synchronize_session=False)
    count = (
        db.query(models.RateLimitHit)
        .filter(models.RateLimitHit.key == key)
        .count()
    )
    if count >= max_hits:
        db.commit()  # persist the prunes
        return False
    db.add(models.RateLimitHit(key=key[:128], created_at=now))
    db.commit()
    return True
