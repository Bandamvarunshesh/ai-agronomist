"""crop image uploads

Revision ID: 20260707_0004
Revises: 20260707_0003
Create Date: 2026-07-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260707_0004"
down_revision = "20260707_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        op.f("ck_crop_images_file_size_bytes_non_negative"),
        "crop_images",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_crop_images_latitude_range"),
        "crop_images",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_crop_images_longitude_range"),
        "crop_images",
        type_="check",
    )
    op.drop_constraint(
        op.f("uq_crop_images_storage_key"),
        "crop_images",
        type_="unique",
    )

    op.alter_column("crop_images", "image_url", new_column_name="file_path")
    op.alter_column("crop_images", "file_size_bytes", new_column_name="file_size")
    op.alter_column("crop_images", "captured_at", new_column_name="uploaded_at")

    op.add_column(
        "crop_images",
        sa.Column(
            "original_filename",
            sa.String(length=255),
            server_default="uploaded_image",
            nullable=False,
        ),
    )

    op.execute(
        "UPDATE crop_images "
        "SET original_filename = regexp_replace(file_path, '^.*/', '') "
        "WHERE file_path IS NOT NULL"
    )
    op.execute(
        "UPDATE crop_images SET content_type = 'application/octet-stream' "
        "WHERE content_type IS NULL"
    )
    op.execute("UPDATE crop_images SET file_size = 0 WHERE file_size IS NULL")
    op.execute("UPDATE crop_images SET uploaded_at = now() WHERE uploaded_at IS NULL")

    op.alter_column("crop_images", "original_filename", server_default=None)
    op.alter_column(
        "crop_images",
        "content_type",
        existing_type=sa.String(length=100),
        nullable=False,
    )
    op.alter_column(
        "crop_images",
        "file_size",
        existing_type=sa.BigInteger(),
        nullable=False,
    )
    op.alter_column(
        "crop_images",
        "uploaded_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )

    op.create_check_constraint(
        op.f("ck_crop_images_file_size_non_negative"),
        "crop_images",
        "file_size >= 0",
    )
    op.create_index(
        op.f("ix_crop_images_uploaded_at"),
        "crop_images",
        ["uploaded_at"],
        unique=False,
    )

    op.drop_column("crop_images", "storage_key")
    op.drop_column("crop_images", "latitude")
    op.drop_column("crop_images", "longitude")
    op.drop_column("crop_images", "notes")
    op.drop_column("crop_images", "metadata")


def downgrade() -> None:
    op.add_column(
        "crop_images",
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column("crop_images", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column(
        "crop_images",
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=True),
    )
    op.add_column(
        "crop_images",
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=True),
    )
    op.add_column(
        "crop_images",
        sa.Column("storage_key", sa.String(length=512), nullable=True),
    )

    op.drop_index(op.f("ix_crop_images_uploaded_at"), table_name="crop_images")
    op.drop_constraint(
        op.f("ck_crop_images_file_size_non_negative"),
        "crop_images",
        type_="check",
    )
    op.drop_column("crop_images", "original_filename")

    op.alter_column(
        "crop_images",
        "uploaded_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=None,
        nullable=True,
    )
    op.alter_column(
        "crop_images",
        "file_size",
        existing_type=sa.BigInteger(),
        nullable=True,
    )
    op.alter_column(
        "crop_images",
        "content_type",
        existing_type=sa.String(length=100),
        nullable=True,
    )

    op.alter_column("crop_images", "uploaded_at", new_column_name="captured_at")
    op.alter_column("crop_images", "file_size", new_column_name="file_size_bytes")
    op.alter_column("crop_images", "file_path", new_column_name="image_url")

    op.create_unique_constraint(
        op.f("uq_crop_images_storage_key"),
        "crop_images",
        ["storage_key"],
    )
    op.create_check_constraint(
        op.f("ck_crop_images_file_size_bytes_non_negative"),
        "crop_images",
        "file_size_bytes IS NULL OR file_size_bytes >= 0",
    )
    op.create_check_constraint(
        op.f("ck_crop_images_latitude_range"),
        "crop_images",
        "latitude IS NULL OR latitude BETWEEN -90 AND 90",
    )
    op.create_check_constraint(
        op.f("ck_crop_images_longitude_range"),
        "crop_images",
        "longitude IS NULL OR longitude BETWEEN -180 AND 180",
    )
