"""Analytics: snapshots + dashboard aggregation."""
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import audit, get_current_user
from ..database import get_db

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("/snapshot", response_model=schemas.AnalyticsOut, status_code=status.HTTP_201_CREATED)
def record_snapshot(
    request: Request,
    payload: schemas.AnalyticsIn,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    snap = models.AnalyticsSnapshot(
        user_id=user.id,
        platform=payload.platform,
        followers=payload.followers,
        impressions=payload.impressions,
        engagement=payload.engagement,
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)
    audit(db, request, "analytics_snapshot", user.id, detail=f"platform={payload.platform}")
    return snap


@router.get("/dashboard", response_model=schemas.DashboardOut)
def dashboard(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    latest: dict[str, models.AnalyticsSnapshot] = {}
    snaps = (
        db.query(models.AnalyticsSnapshot)
        .filter(models.AnalyticsSnapshot.user_id == user.id)
        .order_by(models.AnalyticsSnapshot.recorded_at.desc())
        .all()
    )
    for s in snaps:
        latest.setdefault(s.platform, s)

    by_platform = [
        schemas.AnalyticsOut(
            platform=p,
            followers=s.followers,
            impressions=s.impressions,
            engagement=s.engagement,
            recorded_at=s.recorded_at,
        )
        for p, s in latest.items()
    ]
    totals = {
        "followers": sum(s.followers for s in latest.values()),
        "impressions": sum(s.impressions for s in latest.values()),
        "engagement": sum(s.engagement for s in latest.values()),
    }
    scheduled_count = (
        db.query(func.count(models.ContentPost.id))
        .filter(
            models.ContentPost.user_id == user.id,
            models.ContentPost.status == models.PostStatus.SCHEDULED,
        )
        .scalar()
        or 0
    )
    published_count = (
        db.query(func.count(models.ContentPost.id))
        .filter(
            models.ContentPost.user_id == user.id,
            models.ContentPost.status == models.PostStatus.PUBLISHED,
        )
        .scalar()
        or 0
    )
    return schemas.DashboardOut(
        totals=totals, by_platform=by_platform,
        scheduled_count=scheduled_count, published_count=published_count,
    )
