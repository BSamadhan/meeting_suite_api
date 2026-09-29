"""add meetings host_name

Revision ID: b7c4e91a2f10
Revises: c8e8f781d48d
Create Date: 2026-09-17 09:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7c4e91a2f10"
down_revision: Union[str, Sequence[str], None] = "c8e8f781d48d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "meetings",
        sa.Column("host_name", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("meetings", "host_name")
