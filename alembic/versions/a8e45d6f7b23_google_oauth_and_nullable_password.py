"""google oauth tables and nullable user password

Revision ID: a8e45d6f7b23
Revises: f6c23a4b5d01
Create Date: 2026-09-21 12:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a8e45d6f7b23"
down_revision: Union[str, Sequence[str], None] = "f6c23a4b5d01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.String(length=255),
        nullable=True,
    )
    op.create_table(
        "google_calendar_connections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("google_email", sa.String(length=255), nullable=True),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("token_expiry", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scopes", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            name="uq_google_calendar_connections_user_id",
        ),
    )
    op.create_index(
        op.f("ix_google_calendar_connections_id"),
        "google_calendar_connections",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_google_calendar_connections_user_id"),
        "google_calendar_connections",
        ["user_id"],
        unique=False,
    )
    op.create_table(
        "google_login_tickets",
        sa.Column("ticket", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("ticket"),
    )
    op.create_index(
        op.f("ix_google_login_tickets_user_id"),
        "google_login_tickets",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_google_login_tickets_user_id"),
        table_name="google_login_tickets",
    )
    op.drop_table("google_login_tickets")
    op.drop_index(
        op.f("ix_google_calendar_connections_user_id"),
        table_name="google_calendar_connections",
    )
    op.drop_index(
        op.f("ix_google_calendar_connections_id"),
        table_name="google_calendar_connections",
    )
    op.drop_table("google_calendar_connections")
    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.String(length=255),
        nullable=False,
    )
