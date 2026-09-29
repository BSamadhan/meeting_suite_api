"""add meeting recordings table

Revision ID: e5b12f3a4c90
Revises: d4a91c7e8b22
Create Date: 2026-09-17 17:58:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5b12f3a4c90"
down_revision: Union[str, Sequence[str], None] = "d4a91c7e8b22"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "meeting_recordings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("meeting_id", sa.Integer(), nullable=False),
        sa.Column("file_url", sa.String(length=1000), nullable=False),
        sa.Column("duration", sa.Float(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default="UPLOADED",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["meeting_id"], ["meetings.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_meeting_recordings_id", "meeting_recordings", ["id"])
    op.create_index(
        "ix_meeting_recordings_meeting_id",
        "meeting_recordings",
        ["meeting_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_meeting_recordings_meeting_id", table_name="meeting_recordings")
    op.drop_index("ix_meeting_recordings_id", table_name="meeting_recordings")
    op.drop_table("meeting_recordings")
