"""add meeting actual start and end times

Revision ID: b1c90e2a4d55
Revises: a8e45d6f7b23
Create Date: 2026-09-22 17:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b1c90e2a4d55"
down_revision: Union[str, Sequence[str], None] = "a8e45d6f7b23"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("meetings", sa.Column("actual_start_at", sa.DateTime(), nullable=True))
    op.add_column("meetings", sa.Column("actual_end_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("meetings", "actual_end_at")
    op.drop_column("meetings", "actual_start_at")
