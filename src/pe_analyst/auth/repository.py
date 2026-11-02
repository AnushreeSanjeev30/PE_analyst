"""Persistence for user accounts."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from pe_analyst.db.models import UserModel


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_email(self, email: str) -> UserModel | None:
        return self.session.execute(
            select(UserModel).where(UserModel.email == email)
        ).scalar_one_or_none()

    def get_by_id(self, user_id: str) -> UserModel | None:
        return self.session.get(UserModel, user_id)

    def create(self, email: str, hashed_password: str, role: str = "analyst") -> UserModel:
        user = UserModel(email=email, hashed_password=hashed_password, role=role)
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user


__all__ = ["UserRepository"]
