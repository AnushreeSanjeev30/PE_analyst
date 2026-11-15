"""Deal rooms: create a deal, add the team, and see what has been filed in it."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy.orm import Session

from pe_analyst.auth.dependencies import get_current_user
from pe_analyst.auth.models import UserPublic
from pe_analyst.db.models import DealRoomModel
from pe_analyst.db.session import get_db_session

from .repository import DealRoomError, DealRoomRepository

router = APIRouter(prefix="/deal-rooms", tags=["deal-rooms"])


class DealRoomCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class DealRoomUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None


class MemberAdd(BaseModel):
    email: EmailStr


class MemberSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    email: str
    role: str


class DealRoomSummary(BaseModel):
    id: str
    name: str
    description: str | None
    owner_id: str
    created_at: datetime
    # True when the caller may rename the room, change its members or delete it.
    can_manage: bool
    document_count: int
    analysis_count: int
    member_count: int


class DealRoomDetail(DealRoomSummary):
    members: list[MemberSchema]


def _summary(
    room: DealRoomModel, user: UserPublic, counts: dict[str, int]
) -> DealRoomSummary:
    return DealRoomSummary(
        id=room.id,
        name=room.name,
        description=room.description,
        owner_id=room.owner_id,
        created_at=room.created_at,
        can_manage=DealRoomRepository.can_manage(room, user),
        document_count=counts["documents"],
        analysis_count=counts["analyses"],
        member_count=counts["members"],
    )


def _room_or_404(repository: DealRoomRepository, room_id: str, user: UserPublic) -> DealRoomModel:
    room = repository.get(room_id, user)
    if room is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No deal found with id {room_id}")
    return room


def _managed_room_or_error(
    repository: DealRoomRepository, room_id: str, user: UserPublic
) -> DealRoomModel:
    room = _room_or_404(repository, room_id, user)
    if not repository.can_manage(room, user):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Only the deal owner can change the deal or its team"
        )
    return room


@router.post("", response_model=DealRoomDetail, status_code=status.HTTP_201_CREATED)
def create_room(
    payload: DealRoomCreate,
    session: Session = Depends(get_db_session),  # noqa: B008
    current_user: UserPublic = Depends(get_current_user),  # noqa: B008
) -> DealRoomDetail:
    repository = DealRoomRepository(session)
    room = repository.create(payload.name, payload.description, current_user)
    return _detail(repository, room, current_user)


@router.get("", response_model=list[DealRoomSummary])
def list_rooms(
    session: Session = Depends(get_db_session),  # noqa: B008
    current_user: UserPublic = Depends(get_current_user),  # noqa: B008
) -> list[DealRoomSummary]:
    repository = DealRoomRepository(session)
    rooms = repository.list_for(current_user)
    counts = repository.counts([room.id for room in rooms])
    return [_summary(room, current_user, counts[room.id]) for room in rooms]


def _detail(
    repository: DealRoomRepository, room: DealRoomModel, user: UserPublic
) -> DealRoomDetail:
    summary = _summary(room, user, repository.counts([room.id])[room.id])
    return DealRoomDetail(
        **summary.model_dump(),
        members=[MemberSchema.model_validate(member) for member in repository.members(room)],
    )


@router.get("/{room_id}", response_model=DealRoomDetail)
def get_room(
    room_id: str,
    session: Session = Depends(get_db_session),  # noqa: B008
    current_user: UserPublic = Depends(get_current_user),  # noqa: B008
) -> DealRoomDetail:
    repository = DealRoomRepository(session)
    return _detail(repository, _room_or_404(repository, room_id, current_user), current_user)


@router.patch("/{room_id}", response_model=DealRoomDetail)
def update_room(
    room_id: str,
    payload: DealRoomUpdate,
    session: Session = Depends(get_db_session),  # noqa: B008
    current_user: UserPublic = Depends(get_current_user),  # noqa: B008
) -> DealRoomDetail:
    repository = DealRoomRepository(session)
    room = _managed_room_or_error(repository, room_id, current_user)
    repository.update(room, payload.name, payload.description)
    return _detail(repository, room, current_user)


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room(
    room_id: str,
    session: Session = Depends(get_db_session),  # noqa: B008
    current_user: UserPublic = Depends(get_current_user),  # noqa: B008
) -> Response:
    repository = DealRoomRepository(session)
    repository.delete(_managed_room_or_error(repository, room_id, current_user))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{room_id}/members", response_model=MemberSchema, status_code=status.HTTP_201_CREATED
)
def add_member(
    room_id: str,
    payload: MemberAdd,
    session: Session = Depends(get_db_session),  # noqa: B008
    current_user: UserPublic = Depends(get_current_user),  # noqa: B008
) -> MemberSchema:
    repository = DealRoomRepository(session)
    room = _managed_room_or_error(repository, room_id, current_user)
    try:
        member = repository.add_member(room, payload.email)
    except DealRoomError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error
    return MemberSchema.model_validate(member)


@router.delete("/{room_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    room_id: str,
    user_id: str,
    session: Session = Depends(get_db_session),  # noqa: B008
    current_user: UserPublic = Depends(get_current_user),  # noqa: B008
) -> Response:
    repository = DealRoomRepository(session)
    room = _room_or_404(repository, room_id, current_user)
    # A member may leave on their own; removing anyone else needs the owner.
    if user_id != current_user.id and not repository.can_manage(room, current_user):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Only the deal owner can remove other members"
        )
    if not repository.remove_member(room, user_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That user is not a member of this deal")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router"]
