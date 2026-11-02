"""FastAPI dependencies for authentication and role-based access control."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from pe_analyst.core.config import Settings, get_settings
from pe_analyst.db.session import get_db_session

from .models import UserPublic
from .repository import UserRepository
from .security import InvalidTokenError, decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def get_current_user(
    token: str = Depends(oauth2_scheme),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    session: Session = Depends(get_db_session),  # noqa: B008
) -> UserPublic:
    """Resolve the bearer token into the requesting user, 401 on any failure."""

    unauthorized = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token, settings)
    except InvalidTokenError as error:
        raise unauthorized from error

    user = UserRepository(session).get_by_id(payload.subject)
    if user is None:
        raise unauthorized
    return UserPublic(id=user.id, email=user.email, role=user.role)


def require_role(*roles: str) -> Callable[[UserPublic], UserPublic]:
    """Dependency factory: 403s unless the current user's role is one of ``roles``."""

    def check(current_user: UserPublic = Depends(get_current_user)) -> UserPublic:  # noqa: B008
        if current_user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
        return current_user

    return check


__all__ = ["get_current_user", "oauth2_scheme", "require_role"]
