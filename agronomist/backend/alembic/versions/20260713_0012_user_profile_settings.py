"""user profile settings

Revision ID: 20260713_0012
Revises: 20260713_0011
Create Date: 2026-07-13 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260713_0012"
down_revision = "20260713_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("profile_picture_url", sa.String(length=1024), nullable=True))
    op.add_column("users", sa.Column("default_state", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("default_district", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("default_farm_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "settings",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.create_index(op.f("ix_users_default_farm_id"), "users", ["default_farm_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_users_default_farm_id_farms"),
        "users",
        "farms",
        ["default_farm_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.alter_column("users", "settings", server_default=None)


def downgrade() -> None:
    op.drop_constraint(op.f("fk_users_default_farm_id_farms"), "users", type_="foreignkey")
    op.drop_index(op.f("ix_users_default_farm_id"), table_name="users")
    op.drop_column("users", "settings")
    op.drop_column("users", "default_farm_id")
    op.drop_column("users", "default_district")
    op.drop_column("users", "default_state")
    op.drop_column("users", "profile_picture_url")
