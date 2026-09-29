"""add recording error message

Revision ID: e4f03b5d7a88
Revises: d3e92a4c6f77
Create Date: 2026-09-22 17:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e4f03b5d7a88"
down_revision: Union[str, Sequence[str], None] = "d3e92a4c6f77"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("meeting_recordings")}
    if "error_message" in columns:
        return
    op.add_column(
        "meeting_recordings",
        sa.Column("error_message", sa.String(length=1000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("meeting_recordings", "error_message")
