"""Auth routes: register, login, refresh, logout, email OTP verification. Rate-limited + audited."""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import audit, get_current_user
from ..config import get_settings
from ..database import get_db
from ..email import send_otp_email
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

OTP_PURPOSE = "email_verify"


def _utcnow() -> datetime:
    # Naive UTC everywhere: SQLite does not preserve tzinfo.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _generate_otp_code() -> str:
    # 6 digits, no leading zero: 100000..999999.
    return f"{secrets.randbelow(900000) + 100000}"


def _hash_otp(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def _latest_otp(db: Session, user_id: int) -> models.EmailOTP | None:
    return (
        db.query(models.EmailOTP)
        .filter(
            models.EmailOTP.user_id == user_id,
            models.EmailOTP.purpose == OTP_PURPOSE,
            models.EmailOTP.consumed.is_(False),
        )
        .order_by(models.EmailOTP.created_at.desc())
        .first()
    )


def _create_and_send_otp(db: Session, request: Request, user: models.User) -> None:
    code = _generate_otp_code()
    db.add(
        models.EmailOTP(
            user_id=user.id,
            otp_hash=_hash_otp(code),
            purpose=OTP_PURPOSE,
            expires_at=_utcnow() + timedelta(minutes=settings.otp_ttl_minutes),
        )
    )
    db.commit()
    # send_otp_email never raises; on SMTP failure it logs and returns False,
    # and we still return a generic success to avoid user enumeration.
    send_otp_email(user.email, code, user.name)
    audit(db, request, "otp_sent", user.id)


def _issue_pair(db: Session, user: models.User) -> schemas.TokenPair:
    raw, token_hash, expires_at = create_refresh_token()
    db.add(models.RefreshToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at))
    db.commit()
    return schemas.TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=raw,
        user=schemas.UserOut.model_validate(user),
    )


@router.post("/register", response_model=schemas.RegisterOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.register_rate_limit)
def register(request: Request, payload: schemas.RegisterIn, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = models.User(
        email=payload.email.lower(),
        name=payload.name.strip(),
        password_hash=hash_password(payload.password),
        is_verified=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    audit(db, request, "register", user.id)
    _create_and_send_otp(db, request, user)
    return schemas.RegisterOut(
        user=schemas.UserOut.model_validate(user),
        otp_required=True,
        message="We sent a 6-digit verification code to your email.",
    )


@router.post("/verify-otp", response_model=schemas.TokenPair)
@limiter.limit(settings.login_rate_limit)
def verify_otp(request: Request, payload: schemas.OtpVerifyIn, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email.lower()).first()
    record = _latest_otp(db, user.id) if user else None
    now = _utcnow()
    if user is None or record is None or record.expires_at < now:
        # Generic message: do not reveal whether the email exists.
        audit(db, request, "otp_failed", user.id if user else None)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired code")
    if record.attempts >= settings.otp_max_attempts:
        audit(db, request, "otp_failed", user.id)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Too many attempts, request a new code")
    if not hmac.compare_digest(record.otp_hash, _hash_otp(payload.otp)):
        record.attempts += 1
        db.commit()
        audit(db, request, "otp_failed", user.id)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid code")
    record.consumed = True
    user.is_verified = True
    db.commit()
    audit(db, request, "otp_verified", user.id)
    return _issue_pair(db, user)


@router.post("/resend-otp", response_model=schemas.ResendOut)
@limiter.limit(settings.register_rate_limit)
def resend_otp(request: Request, payload: schemas.OtpResendIn, db: Session = Depends(get_db)):
    generic = schemas.ResendOut(
        otp_required=True,
        message="If that email is registered, a new verification code is on its way.",
    )
    user = db.query(models.User).filter(models.User.email == payload.email.lower()).first()
    if user is None:
        # No enumeration: same response as success.
        return generic
    if user.is_verified:
        return schemas.ResendOut(otp_required=False, message="Email already verified. Please log in.")
    latest = _latest_otp(db, user.id)
    if latest is not None:
        age = (_utcnow() - latest.created_at).total_seconds()
        if age < settings.otp_resend_cooldown_seconds:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Please wait before requesting a new code",
            )
        # Invalidate older codes; only the newest is valid.
        db.query(models.EmailOTP).filter(
            models.EmailOTP.user_id == user.id,
            models.EmailOTP.purpose == OTP_PURPOSE,
            models.EmailOTP.consumed.is_(False),
        ).update({"consumed": True})
        db.commit()
    _create_and_send_otp(db, request, user)
    return schemas.ResendOut(
        otp_required=True,
        message="A new verification code was sent to your email.",
    )


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
    if not user.is_verified:
        audit(db, request, "login_failed", user.id)
        raise HTTPException(status.HTTP_403_FORBIDDEN, "email_not_verified")
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
