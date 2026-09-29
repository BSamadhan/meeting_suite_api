"""add meeting summaries

Revision ID: f5a14c6e8b99
Revises: e4f03b5d7a88
Create Date: 2026-09-22 18:06:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f5a14c6e8b99"
down_revision: Union[str, Sequence[str], None] = "e4f03b5d7a88"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "meeting_summaries" in inspector.get_table_names():
        return

    op.create_table(
        "meeting_summaries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("meeting_id", sa.Integer(), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("key_topics", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["meeting_id"], ["meetings.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_meeting_summaries_id", "meeting_summaries", ["id"])
    op.create_index(
        "ix_meeting_summaries_meeting_id",
        "meeting_summaries",
        ["meeting_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_meeting_summaries_meeting_id", table_name="meeting_summaries")
    op.drop_index("ix_meeting_summaries_id", table_name="meeting_summaries")
    op.drop_table("meeting_summaries")
