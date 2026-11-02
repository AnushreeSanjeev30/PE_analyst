"""JWT authentication and role-based access control."""

from __future__ import annotations

from .dependencies import get_current_user, require_role
from .models import Token, UserCreate, UserPublic
from .repository import UserRepository
from .security import create_access_token, decode_access_token, hash_password, verify_password

__all__ = [
    "Token",
    "UserCreate",
    "UserPublic",
    "UserRepository",
    "create_access_token",
    "decode_access_token",
    "get_current_user",
    "hash_password",
    "require_role",
    "verify_password",
]
