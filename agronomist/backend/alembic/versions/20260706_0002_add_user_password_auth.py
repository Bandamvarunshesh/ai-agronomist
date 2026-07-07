"""add user password auth

Revision ID: 20260706_0002
Revises: 20260706_0001
Create Date: 2026-07-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "20260706_0002"
down_revision = "20260706_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "hashed_password",
            sa.String(length=255),
            server_default="",
            nullable=False,
        ),
    )
    op.alter_column("users", "hashed_password", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "hashed_password")
