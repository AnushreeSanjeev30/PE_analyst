"""Password hashing and JWT issuance/verification."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from pe_analyst.core.config import Settings


class InvalidTokenError(RuntimeError):
    """Raised when a bearer token is missing, expired, or malformed."""


@dataclass(slots=True, frozen=True)
class TokenPayload:
    subject: str
    role: str


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(subject: str, role: str, settings: Settings) -> str:
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "role": role, "exp": expires_at}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str, settings: Settings) -> TokenPayload:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except jwt.PyJWTError as error:
        raise InvalidTokenError(str(error)) from error

    subject = payload.get("sub")
    role = payload.get("role")
    if not subject or not role:
        raise InvalidTokenError("Token payload is missing 'sub' or 'role'")
    return TokenPayload(subject=subject, role=role)


__all__ = [
    "InvalidTokenError",
    "TokenPayload",
    "create_access_token",
    "decode_access_token",
    "hash_password",
    "verify_password",
]
