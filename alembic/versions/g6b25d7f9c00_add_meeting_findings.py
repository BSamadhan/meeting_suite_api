"""add meeting decisions, risks, and action source

Revision ID: g6b25d7f9c00
Revises: f5a14c6e8b99
Create Date: 2026-09-23 11:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "g6b25d7f9c00"
down_revision: Union[str, Sequence[str], None] = "f5a14c6e8b99"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    action_columns = {column["name"] for column in inspector.get_columns("meeting_actions")}
    if "source" not in action_columns:
        op.add_column(
            "meeting_actions",
            sa.Column("source", sa.String(length=50), nullable=False, server_default="manual"),
        )
    if "start_seconds" not in action_columns:
        op.add_column(
            "meeting_actions",
            sa.Column("start_seconds", sa.Float(), nullable=True),
        )
    op.alter_column("meeting_actions", "assigned_to", existing_type=sa.String(length=255), nullable=True)

    if "meeting_decisions" not in inspector.get_table_names():
        op.create_table(
            "meeting_decisions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("meeting_id", sa.Integer(), nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("owner", sa.String(length=255), nullable=True),
            sa.Column("start_seconds", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["meeting_id"], ["meetings.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_meeting_decisions_id", "meeting_decisions", ["id"])
        op.create_index("ix_meeting_decisions_meeting_id", "meeting_decisions", ["meeting_id"])

    if "meeting_risks" not in inspector.get_table_names():
        op.create_table(
            "meeting_risks",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("meeting_id", sa.Integer(), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("impact", sa.String(length=255), nullable=True),
            sa.Column("owner", sa.String(length=255), nullable=True),
            sa.Column("mitigation", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="OPEN"),
            sa.Column("start_seconds", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["meeting_id"], ["meetings.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_meeting_risks_id", "meeting_risks", ["id"])
        op.create_index("ix_meeting_risks_meeting_id", "meeting_risks", ["meeting_id"])


def downgrade() -> None:
    op.drop_index("ix_meeting_risks_meeting_id", table_name="meeting_risks")
    op.drop_index("ix_meeting_risks_id", table_name="meeting_risks")
    op.drop_table("meeting_risks")
    op.drop_index("ix_meeting_decisions_meeting_id", table_name="meeting_decisions")
    op.drop_index("ix_meeting_decisions_id", table_name="meeting_decisions")
    op.drop_table("meeting_decisions")
    op.drop_column("meeting_actions", "start_seconds")
    op.drop_column("meeting_actions", "source")
    op.alter_column("meeting_actions", "assigned_to", existing_type=sa.String(length=255), nullable=False)
