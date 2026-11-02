"""Registration and login."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from pe_analyst.core.config import Settings, get_settings
from pe_analyst.db.session import get_db_session

from .models import Token, UserCreate, UserPublic
from .repository import UserRepository
from .security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register(
    payload: UserCreate,
    session: Session = Depends(get_db_session),  # noqa: B008
) -> UserPublic:
    repository = UserRepository(session)
    if repository.get_by_email(payload.email) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "A user with this email already exists")

    user = repository.create(payload.email, hash_password(payload.password), role="analyst")
    return UserPublic(id=user.id, email=user.email, role=user.role)


@router.post("/token", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),  # noqa: B008
    session: Session = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> Token:
    user = UserRepository(session).get_by_email(form_data.username)
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(user.id, user.role, settings))


__all__ = ["router"]
