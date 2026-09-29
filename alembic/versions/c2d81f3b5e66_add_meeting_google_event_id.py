"""add meeting google event id

Revision ID: c2d81f3b5e66
Revises: b1c90e2a4d55
Create Date: 2026-09-22 17:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c2d81f3b5e66"
down_revision: Union[str, Sequence[str], None] = "b1c90e2a4d55"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("meetings", sa.Column("google_event_id", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("meetings", "google_event_id")
