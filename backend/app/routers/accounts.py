"""Connected social accounts. Tokens are Fernet-encrypted at rest, never returned."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import audit, get_current_user
from ..database import get_db
from ..security import decrypt_token, encrypt_token

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=list[schemas.SocialAccountOut])
def list_accounts(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(models.SocialAccount).filter(models.SocialAccount.user_id == user.id).all()


@router.post("", response_model=schemas.SocialAccountOut, status_code=status.HTTP_201_CREATED)
def connect_account(
    request: Request,
    payload: schemas.SocialAccountIn,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = (
        db.query(models.SocialAccount)
        .filter(
            models.SocialAccount.user_id == user.id,
            models.SocialAccount.platform == payload.platform,
            models.SocialAccount.account_name == payload.account_name.strip(),
        )
        .first()
    )
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Account already connected")
    account = models.SocialAccount(
        user_id=user.id,
        platform=payload.platform,
        account_name=payload.account_name.strip(),
        encrypted_token=encrypt_token(payload.access_token),
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    audit(db, request, "account_connect", user.id, detail=f"platform={payload.platform}")
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def disconnect_account(
    request: Request,
    account_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = (
        db.query(models.SocialAccount)
        .filter(models.SocialAccount.id == account_id, models.SocialAccount.user_id == user.id)
        .first()
    )
    if account is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found")
    platform = account.platform
    db.delete(account)
    db.commit()
    audit(db, request, "account_disconnect", user.id, detail=f"platform={platform}")
    return None


@router.post("/{account_id}/verify")
def verify_account(
    account_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Decrypt-check: proves the stored credential is intact without exposing it."""
    account = (
        db.query(models.SocialAccount)
        .filter(models.SocialAccount.id == account_id, models.SocialAccount.user_id == user.id)
        .first()
    )
    if account is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found")
    try:
        decrypt_token(account.encrypted_token)
    except ValueError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Stored credential is corrupted")
    return {"ok": True, "platform": account.platform}
