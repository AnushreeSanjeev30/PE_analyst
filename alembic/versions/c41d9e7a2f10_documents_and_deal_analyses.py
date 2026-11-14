"""documents and deal analyses

Revision ID: c41d9e7a2f10
Revises: bb224d7fa8ed
Create Date: 2026-11-15 01:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c41d9e7a2f10"
down_revision: str | Sequence[str] | None = "bb224d7fa8ed"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("file_name", sa.String(length=512), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_documents_owner_id", "documents", ["owner_id"])

    op.create_table(
        "deal_analyses",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("document_id", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("recommendation", sa.String(length=16), nullable=True),
        sa.Column("request", sa.JSON(), nullable=False),
        sa.Column("report", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_deal_analyses_owner_id", "deal_analyses", ["owner_id"])


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index("ix_deal_analyses_owner_id", table_name="deal_analyses")
    op.drop_table("deal_analyses")

    op.drop_index("ix_documents_owner_id", table_name="documents")
    op.drop_table("documents")
