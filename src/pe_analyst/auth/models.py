"""Request/response contracts for the auth API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class UserPublic(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    email: str
    role: str


class Token(BaseModel):
    model_config = ConfigDict(frozen=True)

    access_token: str
    token_type: str = "bearer"


__all__ = ["Token", "UserCreate", "UserPublic"]
