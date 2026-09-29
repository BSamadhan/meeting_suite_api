"""add meeting transcript segments

Revision ID: d3e92a4c6f77
Revises: c2d81f3b5e66
Create Date: 2026-09-22 17:32:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d3e92a4c6f77"
down_revision: Union[str, Sequence[str], None] = "c2d81f3b5e66"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "meeting_transcript_segments" in inspector.get_table_names():
        return

    op.create_table(
        "meeting_transcript_segments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("meeting_id", sa.Integer(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("speaker", sa.String(length=255), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("start_seconds", sa.Float(), nullable=True),
        sa.Column("end_seconds", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["meeting_id"], ["meetings.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_meeting_transcript_segments_id",
        "meeting_transcript_segments",
        ["id"],
    )
    op.create_index(
        "ix_meeting_transcript_segments_meeting_id",
        "meeting_transcript_segments",
        ["meeting_id"],
    )
    op.create_index(
        "ix_meeting_transcript_segments_meeting_sequence",
        "meeting_transcript_segments",
        ["meeting_id", "sequence"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_meeting_transcript_segments_meeting_sequence",
        table_name="meeting_transcript_segments",
    )
    op.drop_index(
        "ix_meeting_transcript_segments_meeting_id",
        table_name="meeting_transcript_segments",
    )
    op.drop_index(
        "ix_meeting_transcript_segments_id",
        table_name="meeting_transcript_segments",
    )
    op.drop_table("meeting_transcript_segments")
