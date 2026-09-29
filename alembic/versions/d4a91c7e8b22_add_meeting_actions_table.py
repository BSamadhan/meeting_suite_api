"""add meeting actions table

Revision ID: d4a91c7e8b22
Revises: b7c4e91a2f10
Create Date: 2026-09-17 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4a91c7e8b22"
down_revision: Union[str, Sequence[str], None] = "b7c4e91a2f10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "meeting_actions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("meeting_id", sa.Integer(), nullable=False),
        sa.Column("agenda_id", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("assigned_to", sa.String(length=255), nullable=False),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("department", sa.String(length=100), nullable=True),
        sa.Column("priority", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="OPEN"),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["meeting_id"], ["meetings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agenda_id"], ["meeting_agendas.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
    )
    op.create_index("ix_meeting_actions_id", "meeting_actions", ["id"])
    op.create_index("ix_meeting_actions_meeting_id", "meeting_actions", ["meeting_id"])
    op.create_index("ix_meeting_actions_agenda_id", "meeting_actions", ["agenda_id"])


def downgrade() -> None:
    op.drop_index("ix_meeting_actions_agenda_id", table_name="meeting_actions")
    op.drop_index("ix_meeting_actions_meeting_id", table_name="meeting_actions")
    op.drop_index("ix_meeting_actions_id", table_name="meeting_actions")
    op.drop_table("meeting_actions")
