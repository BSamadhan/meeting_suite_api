"""add meeting participant left_at

Revision ID: f6c23a4b5d01
Revises: e5b12f3a4c90
Create Date: 2026-09-17 18:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6c23a4b5d01"
down_revision: Union[str, Sequence[str], None] = "e5b12f3a4c90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "meeting_participants",
        sa.Column("left_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("meeting_participants", "left_at")
