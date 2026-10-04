"""Comment automation queue."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import audit, get_current_user
from ..database import get_db

router = APIRouter(prefix="/comments", tags=["comments"])


@router.post("/queue", response_model=schemas.CommentOut, status_code=status.HTTP_201_CREATED)
def queue_comment(
    request: Request,
    payload: schemas.CommentIn,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = models.CommentTask(
        user_id=user.id,
        platform=payload.platform,
        post_ref=payload.post_ref.strip(),
        comment_text=payload.comment_text.strip(),
        status="pending",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    audit(db, request, "comment_queue", user.id, detail=f"platform={payload.platform}")
    return task


@router.get("/queue", response_model=list[schemas.CommentOut])
def list_queued(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(models.CommentTask)
        .filter(models.CommentTask.user_id == user.id)
        .order_by(models.CommentTask.created_at.desc())
        .limit(100)
        .all()
    )


@router.post("/queue/{task_id}/done")
def mark_done(
    task_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = (
        db.query(models.CommentTask)
        .filter(models.CommentTask.id == task_id, models.CommentTask.user_id == user.id)
        .first()
    )
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    task.status = "done"
    db.commit()
    return {"ok": True}
