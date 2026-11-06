import os
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.models import Role, User


password_hash = PasswordHash.recommended()
DUMMY_PASSWORD_HASH = password_hash.hash("invalid-login-timing-placeholder")
JWT_ISSUER = "mahara-match"


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, encoded_hash: str) -> bool:
    return password_hash.verify(password, encoded_hash)


def _jwt_settings() -> tuple[str, int]:
    secret = os.getenv("JWT_SECRET_KEY", "")
    if len(secret) < 32:
        raise RuntimeError("JWT_SECRET_KEY must contain at least 32 characters.")
    try:
        expiry_minutes = int(os.getenv("JWT_ACCESS_TOKEN_MINUTES", "30"))
    except ValueError as error:
        raise RuntimeError("JWT_ACCESS_TOKEN_MINUTES must be a positive integer.") from error
    if expiry_minutes < 1:
        raise RuntimeError("JWT_ACCESS_TOKEN_MINUTES must be a positive integer.")
    return secret, expiry_minutes


def create_access_token(user: User) -> tuple[str, int]:
    secret, expiry_minutes = _jwt_settings()
    now = datetime.now(timezone.utc)
    claims = {
        "sub": user.id,
        "role": user.role.value,
        "iss": JWT_ISSUER,
        "iat": now,
        "exp": now + timedelta(minutes=expiry_minutes),
    }
    return jwt.encode(claims, secret, algorithm="HS256"), expiry_minutes * 60


def decode_access_token(token: str) -> dict[str, object]:
    secret, _ = _jwt_settings()
    return jwt.decode(token, secret, algorithms=["HS256"], issuer=JWT_ISSUER)


def role_from_claim(value: object) -> Role | None:
    if not isinstance(value, str):
        return None
    try:
        return Role(value)
    except ValueError:
        return None
