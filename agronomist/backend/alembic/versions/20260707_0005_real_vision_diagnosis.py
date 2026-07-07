"""real vision diagnosis

Revision ID: 20260707_0005
Revises: 20260707_0004
Create Date: 2026-07-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260707_0005"
down_revision = "20260707_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index(op.f("ix_diagnoses_status"), table_name="diagnoses")
    op.drop_constraint(
        op.f("ck_diagnoses_confidence_range"),
        "diagnoses",
        type_="check",
    )

    op.alter_column("diagnoses", "condition_name", new_column_name="disease_name")
    op.alter_column("diagnoses", "confidence", new_column_name="confidence_score")
    op.alter_column("diagnoses", "raw_result", new_column_name="raw_vision_output")

    op.add_column(
        "diagnoses",
        sa.Column(
            "possible_causes",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "diagnoses",
        sa.Column(
            "organic_treatment",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "diagnoses",
        sa.Column(
            "chemical_treatment",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "diagnoses",
        sa.Column(
            "prevention_steps",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "diagnoses",
        sa.Column(
            "escalate_to_human",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )

    op.execute(
        "UPDATE diagnoses SET disease_name = 'unknown' "
        "WHERE disease_name IS NULL OR disease_name = ''"
    )
    op.execute(
        "UPDATE diagnoses SET confidence_score = 0 "
        "WHERE confidence_score IS NULL"
    )
    op.execute(
        "UPDATE diagnoses SET severity = 'unknown' "
        "WHERE severity IS NULL OR severity = ''"
    )

    op.alter_column(
        "diagnoses",
        "disease_name",
        existing_type=sa.String(length=255),
        nullable=False,
    )
    op.alter_column(
        "diagnoses",
        "confidence_score",
        existing_type=sa.Numeric(precision=5, scale=4),
        nullable=False,
    )
    op.alter_column(
        "diagnoses",
        "severity",
        existing_type=sa.String(length=32),
        nullable=False,
    )

    op.create_check_constraint(
        op.f("ck_diagnoses_confidence_score_range"),
        "diagnoses",
        "confidence_score BETWEEN 0 AND 1",
    )

    op.drop_column("diagnoses", "status")
    op.drop_column("diagnoses", "diagnosis_type")
    op.drop_column("diagnoses", "crop_name")
    op.drop_column("diagnoses", "summary")
    op.drop_column("diagnoses", "recommendations")
    op.drop_column("diagnoses", "diagnosed_at")


def downgrade() -> None:
    op.add_column(
        "diagnoses",
        sa.Column(
            "diagnosed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.add_column(
        "diagnoses",
        sa.Column(
            "recommendations",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column("diagnoses", sa.Column("summary", sa.Text(), nullable=True))
    op.add_column(
        "diagnoses",
        sa.Column("crop_name", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "diagnoses",
        sa.Column("diagnosis_type", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "diagnoses",
        sa.Column(
            "status",
            sa.String(length=32),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
    )

    op.drop_constraint(
        op.f("ck_diagnoses_confidence_score_range"),
        "diagnoses",
        type_="check",
    )

    op.alter_column(
        "diagnoses",
        "severity",
        existing_type=sa.String(length=32),
        nullable=True,
    )
    op.alter_column(
        "diagnoses",
        "confidence_score",
        existing_type=sa.Numeric(precision=5, scale=4),
        nullable=True,
    )
    op.alter_column(
        "diagnoses",
        "disease_name",
        existing_type=sa.String(length=255),
        nullable=True,
    )

    op.drop_column("diagnoses", "escalate_to_human")
    op.drop_column("diagnoses", "prevention_steps")
    op.drop_column("diagnoses", "chemical_treatment")
    op.drop_column("diagnoses", "organic_treatment")
    op.drop_column("diagnoses", "possible_causes")

    op.alter_column("diagnoses", "raw_vision_output", new_column_name="raw_result")
    op.alter_column("diagnoses", "confidence_score", new_column_name="confidence")
    op.alter_column("diagnoses", "disease_name", new_column_name="condition_name")

    op.create_check_constraint(
        op.f("ck_diagnoses_confidence_range"),
        "diagnoses",
        "confidence IS NULL OR confidence BETWEEN 0 AND 1",
    )
    op.create_index(
        op.f("ix_diagnoses_status"),
        "diagnoses",
        ["status"],
        unique=False,
    )
