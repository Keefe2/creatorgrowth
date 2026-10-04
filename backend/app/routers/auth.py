"""Auth routes: register, login, refresh, logout. Rate-limited + audited."""
import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import audit, get_current_user
from ..config import get_settings
from ..database import get_db
from ..rate_limit import limiter
from ..security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def _issue_pair(db: Session, user: models.User) -> schemas.TokenPair:
    raw, token_hash, expires_at = create_refresh_token()
    db.add(models.RefreshToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at))
    db.commit()
    return schemas.TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=raw,
        user=schemas.UserOut.model_validate(user),
    )


@router.post("/register", response_model=schemas.TokenPair, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.register_rate_limit)
def register(request: Request, payload: schemas.RegisterIn, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = models.User(
        email=payload.email.lower(),
        name=payload.name.strip(),
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    audit(db, request, "register", user.id)
    return _issue_pair(db, user)


@router.post("/login", response_model=schemas.TokenPair)
@limiter.limit(settings.login_rate_limit)
def login(request: Request, payload: schemas.LoginIn, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email.lower()).first()
    # Constant-time-ish: always run verify to avoid user-enumeration timing leaks.
    candidate_hash = user.password_hash if user else hash_password("dummy-password-for-timing")
    ok = verify_password(payload.password, candidate_hash) and user is not None and user.is_active
    if not ok:
        audit(db, request, "login_failed")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    assert user is not None
    # Rotate: revoke all previous refresh tokens on fresh login.
    db.query(models.RefreshToken).filter(models.RefreshToken.user_id == user.id).update({"revoked": True})
    db.commit()
    audit(db, request, "login", user.id)
    return _issue_pair(db, user)


@router.post("/refresh", response_model=schemas.TokenPair)
def refresh(request: Request, payload: schemas.RefreshIn, db: Session = Depends(get_db)):
    token_hash = hashlib.sha256(payload.refresh_token.encode()).hexdigest()
    record = (
        db.query(models.RefreshToken)
        .filter(models.RefreshToken.token_hash == token_hash, models.RefreshToken.revoked.is_(False))
        .first()
    )
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if record is None or record.expires_at < now:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token")
    # Rotation: revoke the used token, issue a fresh pair.
    record.revoked = True
    db.commit()
    user = db.query(models.User).filter(models.User.id == record.user_id).first()
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")
    audit(db, request, "token_refresh", user.id)
    return _issue_pair(db, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, payload: schemas.RefreshIn, db: Session = Depends(get_db)):
    token_hash = hashlib.sha256(payload.refresh_token.encode()).hexdigest()
    db.query(models.RefreshToken).filter(models.RefreshToken.token_hash == token_hash).update({"revoked": True})
    db.commit()
    audit(db, request, "logout")
    return None


@router.get("/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(get_current_user)):
    return schemas.UserOut.model_validate(user)
