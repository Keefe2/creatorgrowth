"""Content studio: drafts, AI generation, scheduling, publishing."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from .. import ai_engine, models, schemas
from ..auth import audit, get_current_user
from ..database import get_db

router = APIRouter(prefix="/content", tags=["content"])


def _to_out(post: models.ContentPost) -> schemas.ContentOut:
    return schemas.ContentOut(
        id=post.id,
        title=post.title,
        body=post.body,
        platforms=[p for p in post.platforms.split(",") if p],
        status=post.status.value,
        scheduled_at=post.scheduled_at,
        published_at=post.published_at,
        ai_generated=post.ai_generated,
        error=post.error,
        created_at=post.created_at,
    )


@router.post("/generate", response_model=schemas.AIGenerateOut)
def ai_generate(payload: schemas.AIGenerateIn, user: models.User = Depends(get_current_user)):
    return ai_engine.generate(payload)


@router.post("", response_model=schemas.ContentOut, status_code=status.HTTP_201_CREATED)
def create_draft(
    request: Request,
    payload: schemas.ContentIn,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ai: bool = Query(default=False),
):
    post = models.ContentPost(
        user_id=user.id,
        title=payload.title.strip(),
        body=payload.body.strip(),
        platforms=",".join(payload.platforms),
        status=models.PostStatus.DRAFT,
        ai_generated=ai,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    audit(db, request, "content_create", user.id, detail=f"post={post.id}")
    return _to_out(post)


@router.post("/schedule", response_model=schemas.ContentOut, status_code=status.HTTP_201_CREATED)
def schedule_post(
    request: Request,
    payload: schemas.ContentScheduleIn,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    scheduled_at = payload.scheduled_at
    if scheduled_at.tzinfo is None:
        scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
    if scheduled_at <= now:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "scheduled_at must be in the future")
    # Store naive UTC (SQLite drops tzinfo).
    scheduled_at = scheduled_at.astimezone(timezone.utc).replace(tzinfo=None)
    post = models.ContentPost(
        user_id=user.id,
        title=payload.title.strip(),
        body=payload.body.strip(),
        platforms=",".join(payload.platforms),
        status=models.PostStatus.SCHEDULED,
        scheduled_at=scheduled_at,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    audit(db, request, "content_schedule", user.id, detail=f"post={post.id}")
    return _to_out(post)


@router.get("", response_model=list[schemas.ContentOut])
def list_posts(
    status_filter: models.PostStatus | None = Query(default=None, alias="status"),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(models.ContentPost).filter(models.ContentPost.user_id == user.id)
    if status_filter:
        q = q.filter(models.ContentPost.status == status_filter)
    posts = q.order_by(models.ContentPost.created_at.desc()).limit(200).all()
    return [_to_out(p) for p in posts]


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
    request: Request,
    post_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = (
        db.query(models.ContentPost)
        .filter(models.ContentPost.id == post_id, models.ContentPost.user_id == user.id)
        .first()
    )
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Post not found")
    db.delete(post)
    db.commit()
    audit(db, request, "content_delete", user.id, detail=f"post={post_id}")
    return None
