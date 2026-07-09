"""farm recommendations

Revision ID: 20260708_0007
Revises: 20260707_0006
Create Date: 2026-07-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260708_0007"
down_revision = "20260707_0006"
branch_labels = None
depends_on = None


def uuid_pk_column() -> sa.Column:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        server_default=sa.text("gen_random_uuid()"),
        nullable=False,
    )


def timestamp_columns() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def upgrade() -> None:
    op.create_table(
        "farm_recommendations",
        uuid_pk_column(),
        sa.Column("farm_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("farm_health_score", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
        sa.Column(
            "prioritized_recommendations",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "daily_action_plan",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("weekly_summary", sa.Text(), nullable=False),
        sa.Column("confidence_score", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column(
            "context_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "raw_model_output",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        *timestamp_columns(),
        sa.CheckConstraint(
            "farm_health_score BETWEEN 0 AND 100",
            name=op.f("ck_farm_recommendations_farm_health_score_range"),
        ),
        sa.CheckConstraint(
            "confidence_score BETWEEN 0 AND 1",
            name=op.f(
                "ck_farm_recommendations_farm_recommendation_confidence_score_range"
            ),
        ),
        sa.CheckConstraint(
            "risk_level IN ('low', 'moderate', 'high', 'critical')",
            name=op.f(
                "ck_farm_recommendations_farm_recommendation_risk_level_allowed"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["farm_id"],
            ["farms.id"],
            name=op.f("fk_farm_recommendations_farm_id_farms"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_farm_recommendations_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_farm_recommendations")),
    )
    op.create_index(
        op.f("ix_farm_recommendations_farm_id"),
        "farm_recommendations",
        ["farm_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_farm_recommendations_user_id"),
        "farm_recommendations",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_farm_recommendations_risk_level"),
        "farm_recommendations",
        ["risk_level"],
        unique=False,
    )
    op.create_index(
        op.f("ix_farm_recommendations_generated_at"),
        "farm_recommendations",
        ["generated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_farm_recommendations_generated_at"),
        table_name="farm_recommendations",
    )
    op.drop_index(
        op.f("ix_farm_recommendations_risk_level"),
        table_name="farm_recommendations",
    )
    op.drop_index(
        op.f("ix_farm_recommendations_user_id"),
        table_name="farm_recommendations",
    )
    op.drop_index(
        op.f("ix_farm_recommendations_farm_id"),
        table_name="farm_recommendations",
    )
    op.drop_table("farm_recommendations")
