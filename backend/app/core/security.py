import datetime

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError

from app.core.config import settings

_ph = PasswordHasher()
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except VerificationError:
        return False


def _create_token(subject: str, token_type: str, expires_delta: datetime.timedelta) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {"sub": subject, "type": token_type, "iat": now, "exp": now + expires_delta}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_access_token(user_id: str) -> str:
    return _create_token(user_id, "access", datetime.timedelta(minutes=settings.access_token_expire_minutes))


def create_refresh_token(user_id: str) -> str:
    return _create_token(user_id, "refresh", datetime.timedelta(days=settings.refresh_token_expire_days))


def decode_token(token: str, expected_type: str) -> str:
    payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError("wrong token type")
    return payload["sub"]
