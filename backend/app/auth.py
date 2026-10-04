"""Auth dependencies: current-user resolution + audit helper."""
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import models
from .database import get_db
from .security import decode_access_token

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> models.User:
    if creds is None or not creds.credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    try:
        user_id = decode_access_token(creds.credentials)
    except ValueError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e)) from e
    user = db.query(models.User).filter(models.User.id == user_id, models.User.is_active.is_(True)).first()
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")
    return user


def audit(db: Session, request: Request, action: str, user_id: int | None = None, detail: str = "") -> None:
    ip = request.client.host if request.client else ""
    # Never log secrets: truncate detail defensively.
    db.add(models.AuditLog(user_id=user_id, action=action, detail=detail[:500], ip=ip))
    db.commit()
