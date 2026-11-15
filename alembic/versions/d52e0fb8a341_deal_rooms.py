"""deal rooms

Revision ID: d52e0fb8a341
Revises: c41d9e7a2f10
Create Date: 2026-11-15 03:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d52e0fb8a341"
down_revision: str | Sequence[str] | None = "c41d9e7a2f10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        "deal_rooms",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_deal_rooms_owner_id", "deal_rooms", ["owner_id"])

    op.create_table(
        "deal_room_members",
        sa.Column("deal_room_id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), primary_key=True),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_deal_room_members_user_id", "deal_room_members", ["user_id"])

    op.add_column("documents", sa.Column("deal_room_id", sa.String(length=36), nullable=True))
    op.create_index("ix_documents_deal_room_id", "documents", ["deal_room_id"])

    op.add_column("deal_analyses", sa.Column("deal_room_id", sa.String(length=36), nullable=True))
    op.create_index("ix_deal_analyses_deal_room_id", "deal_analyses", ["deal_room_id"])


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index("ix_deal_analyses_deal_room_id", table_name="deal_analyses")
    op.drop_column("deal_analyses", "deal_room_id")

    op.drop_index("ix_documents_deal_room_id", table_name="documents")
    op.drop_column("documents", "deal_room_id")

    op.drop_index("ix_deal_room_members_user_id", table_name="deal_room_members")
    op.drop_table("deal_room_members")

    op.drop_index("ix_deal_rooms_owner_id", table_name="deal_rooms")
    op.drop_table("deal_rooms")
