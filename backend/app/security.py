"""Cryptographic primitives: password hashing, JWT, Fernet token encryption."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from cryptography.fernet import Fernet, InvalidToken

from .config import get_settings

settings = get_settings()

_BCRYPT_ROUNDS = 12


def hash_password(password: str) -> str:
    if not 8 <= len(password) <= 128:
        raise ValueError("Password must be 8-128 characters")
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except (ValueError, TypeError):
        return False


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _db_now() -> datetime:
    """Naive UTC for database comparisons (SQLite drops tzinfo)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def create_access_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": _now(),
        "exp": _now() + timedelta(minutes=settings.access_token_minutes),
        "jti": secrets.token_hex(16),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token() -> tuple[str, str, datetime]:
    """Returns (raw_token, sha256_hash, expires_at). Only the hash is stored."""
    raw = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    expires_at = _db_now() + timedelta(days=settings.refresh_token_days)
    return raw, token_hash, expires_at


def decode_access_token(token: str) -> int:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as e:
        raise ValueError("Token expired") from e
    except jwt.InvalidTokenError as e:
        raise ValueError("Invalid token") from e
    if payload.get("type") != "access":
        raise ValueError("Wrong token type")
    return int(payload["sub"])


def _fernet() -> Fernet:
    key = settings.encryption_key.encode()
    return Fernet(key)


def encrypt_token(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as e:
        raise ValueError("Could not decrypt stored credential") from e
