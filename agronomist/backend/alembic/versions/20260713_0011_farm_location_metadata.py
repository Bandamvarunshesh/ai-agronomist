"""farm location metadata

Revision ID: 20260713_0011
Revises: 20260708_0010
Create Date: 2026-07-13 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "20260713_0011"
down_revision = "20260708_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("farms", sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=True))
    op.add_column("farms", sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=True))
    op.add_column("farms", sa.Column("formatted_address", sa.String(length=500), nullable=True))
    op.add_column("farms", sa.Column("locality", sa.String(length=100), nullable=True))
    op.add_column("farms", sa.Column("country", sa.String(length=100), nullable=True))
    op.add_column("farms", sa.Column("postal_code", sa.String(length=20), nullable=True))
    op.add_column(
        "farms",
        sa.Column(
            "location_source",
            sa.String(length=32),
            server_default=sa.text("'manual'"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        op.f("ck_farms_latitude_range"),
        "farms",
        "latitude IS NULL OR latitude BETWEEN -90 AND 90",
    )
    op.create_check_constraint(
        op.f("ck_farms_longitude_range"),
        "farms",
        "longitude IS NULL OR longitude BETWEEN -180 AND 180",
    )
    op.create_check_constraint(
        op.f("ck_farms_location_source"),
        "farms",
        "location_source IN ('current_location', 'map_selection', 'manual')",
    )
    op.alter_column("farms", "location_source", server_default=None)


def downgrade() -> None:
    op.drop_constraint(op.f("ck_farms_location_source"), "farms", type_="check")
    op.drop_constraint(op.f("ck_farms_longitude_range"), "farms", type_="check")
    op.drop_constraint(op.f("ck_farms_latitude_range"), "farms", type_="check")
    op.drop_column("farms", "location_source")
    op.drop_column("farms", "postal_code")
    op.drop_column("farms", "country")
    op.drop_column("farms", "locality")
    op.drop_column("farms", "formatted_address")
    op.drop_column("farms", "longitude")
    op.drop_column("farms", "latitude")
