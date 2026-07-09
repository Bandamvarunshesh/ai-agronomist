"""smart notifications

Revision ID: 20260708_0008
Revises: 20260708_0007
Create Date: 2026-07-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260708_0008"
down_revision = "20260708_0007"
branch_labels = None
depends_on = None


DEFAULT_ENABLED_TYPES_JSON = """{
  "weather_alert": true,
  "irrigation_reminder": true,
  "fertilizer_reminder": true,
  "disease_alert": true,
  "crop_stage_reminder": true,
  "farming_task_reminder": true,
  "daily_ai_summary": true,
  "weekly_ai_summary": true,
  "high_risk_alert": true,
  "recommendation_generated": true,
  "farm_health_alert": true
}"""


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
    op.add_column(
        "notifications",
        sa.Column(
            "source",
            sa.String(length=64),
            server_default=sa.text("'system'"),
            nullable=False,
        ),
    )
    op.add_column(
        "notifications",
        sa.Column("dedupe_key", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "notifications",
        sa.Column("deep_link", sa.String(length=1024), nullable=True),
    )
    op.add_column(
        "notifications",
        sa.Column("push_title", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "notifications",
        sa.Column("push_body", sa.Text(), nullable=True),
    )
    op.add_column(
        "notifications",
        sa.Column(
            "push_data",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "notifications",
        sa.Column(
            "delivery_status",
            sa.String(length=32),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
    )
    op.add_column(
        "notifications",
        sa.Column("delivery_error", sa.Text(), nullable=True),
    )
    op.create_index(
        op.f("ix_notifications_source"),
        "notifications",
        ["source"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notifications_dedupe_key"),
        "notifications",
        ["dedupe_key"],
        unique=True,
    )
    op.create_index(
        op.f("ix_notifications_delivery_status"),
        "notifications",
        ["delivery_status"],
        unique=False,
    )

    op.create_table(
        "notification_preferences",
        uuid_pk_column(),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "notifications_enabled",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "in_app_enabled",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "push_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "email_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "sms_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "enabled_types",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text(f"'{DEFAULT_ENABLED_TYPES_JSON}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "quiet_hours_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("quiet_hours_start", sa.String(length=5), nullable=True),
        sa.Column("quiet_hours_end", sa.String(length=5), nullable=True),
        sa.Column(
            "timezone",
            sa.String(length=64),
            server_default=sa.text("'UTC'"),
            nullable=False,
        ),
        sa.Column("push_token", sa.String(length=512), nullable=True),
        sa.Column("push_platform", sa.String(length=32), nullable=True),
        sa.Column("push_provider", sa.String(length=32), nullable=True),
        sa.Column(
            "device_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_notification_preferences_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notification_preferences")),
        sa.UniqueConstraint(
            "user_id",
            name=op.f("uq_notification_preferences_user_id"),
        ),
    )
    op.create_index(
        op.f("ix_notification_preferences_user_id"),
        "notification_preferences",
        ["user_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_notification_preferences_user_id"),
        table_name="notification_preferences",
    )
    op.drop_table("notification_preferences")

    op.drop_index(op.f("ix_notifications_delivery_status"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_dedupe_key"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_source"), table_name="notifications")
    op.drop_column("notifications", "delivery_error")
    op.drop_column("notifications", "delivery_status")
    op.drop_column("notifications", "push_data")
    op.drop_column("notifications", "push_body")
    op.drop_column("notifications", "push_title")
    op.drop_column("notifications", "deep_link")
    op.drop_column("notifications", "dedupe_key")
    op.drop_column("notifications", "source")
