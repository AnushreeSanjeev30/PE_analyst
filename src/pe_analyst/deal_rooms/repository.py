"""Persistence and access rules for deal rooms.

A deal room is the unit of sharing. Its owner and its members can read every document and
analysis filed in it; only the owner (or an admin) can change who the members are, rename it
or delete it. Anything not filed in a room stays private to the user who created it.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from pe_analyst.auth.models import UserPublic
from pe_analyst.db.models import (
    DealAnalysisModel,
    DealRoomMemberModel,
    DealRoomModel,
    DocumentModel,
    UserModel,
)

ADMIN_ROLE = "admin"


@dataclass(slots=True)
class RoomMember:
    user_id: str
    email: str
    # "owner" | "member"
    role: str


class DealRoomError(ValueError):
    """A request the caller could fix: unknown email, duplicate member, and so on."""


def accessible_room_ids(session: Session, user: UserPublic) -> set[str]:
    """Ids of every deal room ``user`` owns or is a member of (all rooms for an admin)."""

    if user.role == ADMIN_ROLE:
        return set(session.execute(select(DealRoomModel.id)).scalars())
    owned = session.execute(
        select(DealRoomModel.id).where(DealRoomModel.owner_id == user.id)
    ).scalars()
    joined = session.execute(
        select(DealRoomMemberModel.deal_room_id).where(DealRoomMemberModel.user_id == user.id)
    ).scalars()
    return set(owned) | set(joined)


class DealRoomRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Rooms
    # ------------------------------------------------------------------

    def create(self, name: str, description: str | None, owner: UserPublic) -> DealRoomModel:
        room = DealRoomModel(name=name.strip(), description=description, owner_id=owner.id)
        self.session.add(room)
        self.session.commit()
        self.session.refresh(room)
        return room

    def get(self, room_id: str, user: UserPublic) -> DealRoomModel | None:
        """The room, or None when it doesn't exist or ``user`` has no access to it."""

        room = self.session.get(DealRoomModel, room_id)
        if room is None or room.id not in accessible_room_ids(self.session, user):
            return None
        return room

    def list_for(self, user: UserPublic) -> list[DealRoomModel]:
        ids = accessible_room_ids(self.session, user)
        if not ids:
            return []
        statement = (
            select(DealRoomModel)
            .where(DealRoomModel.id.in_(ids))
            .order_by(DealRoomModel.created_at.desc())
        )
        return list(self.session.execute(statement).scalars())

    @staticmethod
    def can_manage(room: DealRoomModel, user: UserPublic) -> bool:
        return user.role == ADMIN_ROLE or room.owner_id == user.id

    def update(self, room: DealRoomModel, name: str | None, description: str | None) -> None:
        if name is not None:
            room.name = name.strip()
        if description is not None:
            room.description = description
        self.session.commit()

    def delete(self, room: DealRoomModel) -> None:
        """Delete the room. Its documents and analyses are kept and revert to their owners."""

        self.session.execute(
            update(DocumentModel)
            .where(DocumentModel.deal_room_id == room.id)
            .values(deal_room_id=None)
        )
        self.session.execute(
            update(DealAnalysisModel)
            .where(DealAnalysisModel.deal_room_id == room.id)
            .values(deal_room_id=None)
        )
        self.session.execute(
            delete(DealRoomMemberModel).where(DealRoomMemberModel.deal_room_id == room.id)
        )
        self.session.delete(room)
        self.session.commit()

    def counts(self, room_ids: list[str]) -> dict[str, dict[str, int]]:
        """Document, analysis and member counts per room, for the list view."""

        result = {
            room_id: {"documents": 0, "analyses": 0, "members": 1} for room_id in room_ids
        }
        if not room_ids:
            return result
        for key, model, column in (
            ("documents", DocumentModel, DocumentModel.deal_room_id),
            ("analyses", DealAnalysisModel, DealAnalysisModel.deal_room_id),
            ("members", DealRoomMemberModel, DealRoomMemberModel.deal_room_id),
        ):
            rows = self.session.execute(
                select(column, func.count()).select_from(model).where(column.in_(room_ids))
                .group_by(column)
            ).all()
            for room_id, count in rows:
                # The owner is not stored as a member row, hence the starting 1.
                if room_id is None:
                    continue
                result[room_id][key] = count + (1 if key == "members" else 0)
        return result

    # ------------------------------------------------------------------
    # Members
    # ------------------------------------------------------------------

    def members(self, room: DealRoomModel) -> list[RoomMember]:
        owner = self.session.get(UserModel, room.owner_id)
        members = [
            RoomMember(room.owner_id, owner.email if owner else "(deleted user)", "owner")
        ]
        rows = self.session.execute(
            select(UserModel)
            .join(DealRoomMemberModel, DealRoomMemberModel.user_id == UserModel.id)
            .where(DealRoomMemberModel.deal_room_id == room.id)
            .order_by(UserModel.email)
        ).scalars()
        members.extend(RoomMember(user.id, user.email, "member") for user in rows)
        return members

    def add_member(self, room: DealRoomModel, email: str) -> RoomMember:
        user = self.session.execute(
            select(UserModel).where(func.lower(UserModel.email) == email.strip().lower())
        ).scalar_one_or_none()
        if user is None:
            raise DealRoomError(
                f"No account exists for {email}. Ask them to register first, then add them."
            )
        if user.id == room.owner_id:
            raise DealRoomError(f"{email} already owns this deal.")
        existing = self.session.get(DealRoomMemberModel, (room.id, user.id))
        if existing is not None:
            raise DealRoomError(f"{email} is already on this deal.")
        self.session.add(DealRoomMemberModel(deal_room_id=room.id, user_id=user.id))
        self.session.commit()
        return RoomMember(user.id, user.email, "member")

    def remove_member(self, room: DealRoomModel, user_id: str) -> bool:
        member = self.session.get(DealRoomMemberModel, (room.id, user_id))
        if member is None:
            return False
        self.session.delete(member)
        self.session.commit()
        return True


__all__ = [
    "ADMIN_ROLE",
    "DealRoomError",
    "DealRoomRepository",
    "RoomMember",
    "accessible_room_ids",
]
