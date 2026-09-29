"""add meeting ai messages

Revision ID: h7c36e8a0d11
Revises: g6b25d7f9c00
Create Date: 2026-09-23 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h7c36e8a0d11"
down_revision: Union[str, Sequence[str], None] = "g6b25d7f9c00"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "meeting_ai_messages" in inspector.get_table_names():
        return
    op.create_table(
        "meeting_ai_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("meeting_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["meeting_id"], ["meetings.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_meeting_ai_messages_id", "meeting_ai_messages", ["id"])
    op.create_index(
        "ix_meeting_ai_messages_meeting_id",
        "meeting_ai_messages",
        ["meeting_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_meeting_ai_messages_meeting_id", table_name="meeting_ai_messages")
    op.drop_index("ix_meeting_ai_messages_id", table_name="meeting_ai_messages")
    op.drop_table("meeting_ai_messages")
