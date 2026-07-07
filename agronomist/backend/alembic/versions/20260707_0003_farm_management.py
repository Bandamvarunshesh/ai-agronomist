"""farm management

Revision ID: 20260707_0003
Revises: 20260706_0002
Create Date: 2026-07-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260707_0003"
down_revision = "20260706_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        op.f("ck_farms_area_acres_non_negative"),
        "farms",
        type_="check",
    )
    op.drop_constraint(op.f("ck_farms_latitude_range"), "farms", type_="check")
    op.drop_constraint(op.f("ck_farms_longitude_range"), "farms", type_="check")
    op.drop_index(op.f("ix_farms_crop_type"), table_name="farms")

    op.alter_column("farms", "name", new_column_name="farm_name")
    op.alter_column("farms", "crop_type", new_column_name="crop")
    op.alter_column("farms", "location_name", new_column_name="location")
    op.alter_column("farms", "area_acres", new_column_name="land_size_acres")
    op.alter_column("farms", "planting_date", new_column_name="sowing_date")

    op.add_column(
        "farms",
        sa.Column(
            "village",
            sa.String(length=100),
            server_default="Unknown",
            nullable=False,
        ),
    )
    op.add_column(
        "farms",
        sa.Column(
            "district",
            sa.String(length=100),
            server_default="Unknown",
            nullable=False,
        ),
    )
    op.add_column(
        "farms",
        sa.Column(
            "state",
            sa.String(length=100),
            server_default="Unknown",
            nullable=False,
        ),
    )
    op.add_column(
        "farms",
        sa.Column("irrigation_type", sa.String(length=100), nullable=True),
    )

    op.execute("UPDATE farms SET crop = 'Unknown' WHERE crop IS NULL")
    op.execute("UPDATE farms SET location = 'Unknown' WHERE location IS NULL")
    op.execute("UPDATE farms SET land_size_acres = 0 WHERE land_size_acres IS NULL")

    op.alter_column("farms", "crop", existing_type=sa.String(length=100), nullable=False)
    op.alter_column(
        "farms",
        "location",
        existing_type=sa.String(length=255),
        nullable=False,
    )
    op.alter_column(
        "farms",
        "land_size_acres",
        existing_type=sa.Numeric(precision=10, scale=2),
        nullable=False,
    )
    op.alter_column("farms", "village", server_default=None)
    op.alter_column("farms", "district", server_default=None)
    op.alter_column("farms", "state", server_default=None)

    op.create_check_constraint(
        op.f("ck_farms_land_size_acres_non_negative"),
        "farms",
        "land_size_acres >= 0",
    )
    op.create_index(op.f("ix_farms_crop"), "farms", ["crop"], unique=False)

    op.drop_column("farms", "latitude")
    op.drop_column("farms", "longitude")
    op.drop_column("farms", "notes")
    op.drop_column("farms", "metadata")


def downgrade() -> None:
    op.add_column(
        "farms",
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column("farms", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column(
        "farms",
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=True),
    )
    op.add_column(
        "farms",
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=True),
    )

    op.drop_index(op.f("ix_farms_crop"), table_name="farms")
    op.drop_constraint(
        op.f("ck_farms_land_size_acres_non_negative"),
        "farms",
        type_="check",
    )

    op.drop_column("farms", "irrigation_type")
    op.drop_column("farms", "state")
    op.drop_column("farms", "district")
    op.drop_column("farms", "village")

    op.alter_column("farms", "sowing_date", new_column_name="planting_date")
    op.alter_column("farms", "land_size_acres", new_column_name="area_acres")
    op.alter_column("farms", "location", new_column_name="location_name")
    op.alter_column("farms", "crop", new_column_name="crop_type")
    op.alter_column("farms", "farm_name", new_column_name="name")

    op.alter_column(
        "farms",
        "crop_type",
        existing_type=sa.String(length=100),
        nullable=True,
    )
    op.alter_column(
        "farms",
        "location_name",
        existing_type=sa.String(length=255),
        nullable=True,
    )
    op.alter_column(
        "farms",
        "area_acres",
        existing_type=sa.Numeric(precision=10, scale=2),
        nullable=True,
    )

    op.create_index(
        op.f("ix_farms_crop_type"),
        "farms",
        ["crop_type"],
        unique=False,
    )
    op.create_check_constraint(
        op.f("ck_farms_area_acres_non_negative"),
        "farms",
        "area_acres IS NULL OR area_acres >= 0",
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
