"""initial database foundation

Revision ID: 20260706_0001
Revises:
Create Date: 2026-07-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260706_0001"
down_revision = None
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
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    op.create_table(
        "users",
        uuid_pk_column(),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone_number", sa.String(length=32), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column(
            "preferred_language",
            sa.String(length=16),
            server_default=sa.text("'en'"),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.String(length=32),
            server_default=sa.text("'farmer'"),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        *timestamp_columns(),
        sa.CheckConstraint(
            "email IS NOT NULL OR phone_number IS NOT NULL",
            name=op.f("ck_users_contact_present"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(
        op.f("ix_users_phone_number"),
        "users",
        ["phone_number"],
        unique=True,
    )

    op.create_table(
        "farms",
        uuid_pk_column(),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("location_name", sa.String(length=255), nullable=True),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("area_acres", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("crop_type", sa.String(length=100), nullable=True),
        sa.Column("soil_type", sa.String(length=100), nullable=True),
        sa.Column("planting_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        *timestamp_columns(),
        sa.CheckConstraint(
            "area_acres IS NULL OR area_acres >= 0",
            name=op.f("ck_farms_area_acres_non_negative"),
        ),
        sa.CheckConstraint(
            "latitude IS NULL OR latitude BETWEEN -90 AND 90",
            name=op.f("ck_farms_latitude_range"),
        ),
        sa.CheckConstraint(
            "longitude IS NULL OR longitude BETWEEN -180 AND 180",
            name=op.f("ck_farms_longitude_range"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_farms_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_farms")),
    )
    op.create_index(op.f("ix_farms_crop_type"), "farms", ["crop_type"], unique=False)
    op.create_index(op.f("ix_farms_user_id"), "farms", ["user_id"], unique=False)

    op.create_table(
        "chat_sessions",
        uuid_pk_column(),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("farm_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column(
            "channel",
            sa.String(length=32),
            server_default=sa.text("'web'"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        *timestamp_columns(),
        sa.CheckConstraint(
            "status IN ('active', 'archived', 'closed')",
            name=op.f("ck_chat_sessions_status_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["farm_id"],
            ["farms.id"],
            name=op.f("fk_chat_sessions_farm_id_farms"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_chat_sessions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chat_sessions")),
    )
    op.create_index(
        op.f("ix_chat_sessions_farm_id"),
        "chat_sessions",
        ["farm_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_chat_sessions_status"),
        "chat_sessions",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_chat_sessions_user_id"),
        "chat_sessions",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "crop_images",
        uuid_pk_column(),
        sa.Column("farm_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("image_url", sa.String(length=2048), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=True),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        *timestamp_columns(),
        sa.CheckConstraint(
            "file_size_bytes IS NULL OR file_size_bytes >= 0",
            name=op.f("ck_crop_images_file_size_bytes_non_negative"),
        ),
        sa.CheckConstraint(
            "latitude IS NULL OR latitude BETWEEN -90 AND 90",
            name=op.f("ck_crop_images_latitude_range"),
        ),
        sa.CheckConstraint(
            "longitude IS NULL OR longitude BETWEEN -180 AND 180",
            name=op.f("ck_crop_images_longitude_range"),
        ),
        sa.ForeignKeyConstraint(
            ["farm_id"],
            ["farms.id"],
            name=op.f("fk_crop_images_farm_id_farms"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_crop_images_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_crop_images")),
        sa.UniqueConstraint("storage_key", name=op.f("uq_crop_images_storage_key")),
    )
    op.create_index(
        op.f("ix_crop_images_farm_id"),
        "crop_images",
        ["farm_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_crop_images_user_id"),
        "crop_images",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "crop_stage_calendars",
        uuid_pk_column(),
        sa.Column("farm_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("crop_name", sa.String(length=100), nullable=False),
        sa.Column("stage_name", sa.String(length=100), nullable=False),
        sa.Column("stage_order", sa.Integer(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("expected_start_day", sa.Integer(), nullable=True),
        sa.Column("expected_end_day", sa.Integer(), nullable=True),
        sa.Column(
            "tasks",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "recommendations",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        *timestamp_columns(),
        sa.CheckConstraint(
            "expected_end_day IS NULL OR expected_end_day >= 0",
            name=op.f("ck_crop_stage_calendars_expected_end_day_non_negative"),
        ),
        sa.CheckConstraint(
            "expected_start_day IS NULL OR expected_start_day >= 0",
            name=op.f("ck_crop_stage_calendars_expected_start_day_non_negative"),
        ),
        sa.CheckConstraint(
            "stage_order IS NULL OR stage_order >= 0",
            name=op.f("ck_crop_stage_calendars_stage_order_non_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["farm_id"],
            ["farms.id"],
            name=op.f("fk_crop_stage_calendars_farm_id_farms"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_crop_stage_calendars")),
        sa.UniqueConstraint(
            "farm_id",
            "crop_name",
            "stage_name",
            name=op.f("uq_crop_stage_calendars_farm_crop_stage"),
        ),
    )
    op.create_index(
        op.f("ix_crop_stage_calendars_crop_name"),
        "crop_stage_calendars",
        ["crop_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_crop_stage_calendars_farm_id"),
        "crop_stage_calendars",
        ["farm_id"],
        unique=False,
    )

    op.create_table(
        "escalation_contacts",
        uuid_pk_column(),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("farm_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=100), nullable=True),
        sa.Column("organization", sa.String(length=255), nullable=True),
        sa.Column("phone_number", sa.String(length=32), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column(
            "preferred_channel",
            sa.String(length=32),
            server_default=sa.text("'phone'"),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["farm_id"],
            ["farms.id"],
            name=op.f("fk_escalation_contacts_farm_id_farms"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_escalation_contacts_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_escalation_contacts")),
    )
    op.create_index(
        op.f("ix_escalation_contacts_farm_id"),
        "escalation_contacts",
        ["farm_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_escalation_contacts_is_active"),
        "escalation_contacts",
        ["is_active"],
        unique=False,
    )
    op.create_index(
        op.f("ix_escalation_contacts_user_id"),
        "escalation_contacts",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "fertilizer_history",
        uuid_pk_column(),
        sa.Column("farm_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("applied_on", sa.Date(), nullable=False),
        sa.Column("fertilizer_name", sa.String(length=255), nullable=False),
        sa.Column("fertilizer_type", sa.String(length=100), nullable=True),
        sa.Column("quantity", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column("application_method", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        *timestamp_columns(),
        sa.CheckConstraint(
            "quantity IS NULL OR quantity >= 0",
            name=op.f("ck_fertilizer_history_quantity_non_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["farm_id"],
            ["farms.id"],
            name=op.f("fk_fertilizer_history_farm_id_farms"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fertilizer_history")),
    )
    op.create_index(
        op.f("ix_fertilizer_history_applied_on"),
        "fertilizer_history",
        ["applied_on"],
        unique=False,
    )
    op.create_index(
        op.f("ix_fertilizer_history_farm_id"),
        "fertilizer_history",
        ["farm_id"],
        unique=False,
    )

    op.create_table(
        "timeline_events",
        uuid_pk_column(),
        sa.Column("farm_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column(
            "source",
            sa.String(length=32),
            server_default=sa.text("'manual'"),
            nullable=False,
        ),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["farm_id"],
            ["farms.id"],
            name=op.f("fk_timeline_events_farm_id_farms"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_timeline_events_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_timeline_events")),
    )
    op.create_index(
        op.f("ix_timeline_events_event_date"),
        "timeline_events",
        ["event_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_timeline_events_event_type"),
        "timeline_events",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_timeline_events_farm_id"),
        "timeline_events",
        ["farm_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_timeline_events_user_id"),
        "timeline_events",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "chat_messages",
        uuid_pk_column(),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        *timestamp_columns(),
        sa.CheckConstraint(
            "role IN ('user', 'assistant', 'system', 'tool')",
            name=op.f("ck_chat_messages_role_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["chat_sessions.id"],
            name=op.f("fk_chat_messages_session_id_chat_sessions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_chat_messages_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chat_messages")),
    )
    op.create_index(
        op.f("ix_chat_messages_role"),
        "chat_messages",
        ["role"],
        unique=False,
    )
    op.create_index(
        op.f("ix_chat_messages_sent_at"),
        "chat_messages",
        ["sent_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_chat_messages_session_id"),
        "chat_messages",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_chat_messages_user_id"),
        "chat_messages",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "diagnoses",
        uuid_pk_column(),
        sa.Column("farm_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("crop_image_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("diagnosis_type", sa.String(length=100), nullable=True),
        sa.Column("crop_name", sa.String(length=100), nullable=True),
        sa.Column("condition_name", sa.String(length=255), nullable=True),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("severity", sa.String(length=32), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "recommendations",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "raw_result",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "diagnosed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        *timestamp_columns(),
        sa.CheckConstraint(
            "confidence IS NULL OR confidence BETWEEN 0 AND 1",
            name=op.f("ck_diagnoses_confidence_range"),
        ),
        sa.ForeignKeyConstraint(
            ["crop_image_id"],
            ["crop_images.id"],
            name=op.f("fk_diagnoses_crop_image_id_crop_images"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["farm_id"],
            ["farms.id"],
            name=op.f("fk_diagnoses_farm_id_farms"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_diagnoses_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_diagnoses")),
    )
    op.create_index(
        op.f("ix_diagnoses_crop_image_id"),
        "diagnoses",
        ["crop_image_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_diagnoses_farm_id"),
        "diagnoses",
        ["farm_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_diagnoses_severity"),
        "diagnoses",
        ["severity"],
        unique=False,
    )
    op.create_index(
        op.f("ix_diagnoses_status"),
        "diagnoses",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_diagnoses_user_id"),
        "diagnoses",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "escalations",
        uuid_pk_column(),
        sa.Column("farm_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("diagnosis_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default=sa.text("'open'"),
            nullable=False,
        ),
        sa.Column(
            "priority",
            sa.String(length=32),
            server_default=sa.text("'normal'"),
            nullable=False,
        ),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column(
            "escalated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["contact_id"],
            ["escalation_contacts.id"],
            name=op.f("fk_escalations_contact_id_escalation_contacts"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["diagnosis_id"],
            ["diagnoses.id"],
            name=op.f("fk_escalations_diagnosis_id_diagnoses"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["farm_id"],
            ["farms.id"],
            name=op.f("fk_escalations_farm_id_farms"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_escalations_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_escalations")),
    )
    op.create_index(
        op.f("ix_escalations_contact_id"),
        "escalations",
        ["contact_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_escalations_diagnosis_id"),
        "escalations",
        ["diagnosis_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_escalations_escalated_at"),
        "escalations",
        ["escalated_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_escalations_farm_id"),
        "escalations",
        ["farm_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_escalations_priority"),
        "escalations",
        ["priority"],
        unique=False,
    )
    op.create_index(
        op.f("ix_escalations_resolved_at"),
        "escalations",
        ["resolved_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_escalations_status"),
        "escalations",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_escalations_user_id"),
        "escalations",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "notifications",
        uuid_pk_column(),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("farm_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("diagnosis_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notification_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "priority",
            sa.String(length=32),
            server_default=sa.text("'normal'"),
            nullable=False,
        ),
        sa.Column(
            "channel",
            sa.String(length=32),
            server_default=sa.text("'in_app'"),
            nullable=False,
        ),
        sa.Column(
            "is_read",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["diagnosis_id"],
            ["diagnoses.id"],
            name=op.f("fk_notifications_diagnosis_id_diagnoses"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["farm_id"],
            ["farms.id"],
            name=op.f("fk_notifications_farm_id_farms"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_notifications_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notifications")),
    )
    op.create_index(
        op.f("ix_notifications_diagnosis_id"),
        "notifications",
        ["diagnosis_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notifications_farm_id"),
        "notifications",
        ["farm_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notifications_is_read"),
        "notifications",
        ["is_read"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notifications_notification_type"),
        "notifications",
        ["notification_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notifications_priority"),
        "notifications",
        ["priority"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notifications_scheduled_for"),
        "notifications",
        ["scheduled_for"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notifications_sent_at"),
        "notifications",
        ["sent_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notifications_user_id"),
        "notifications",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("escalations")
    op.drop_table("diagnoses")
    op.drop_table("chat_messages")
    op.drop_table("timeline_events")
    op.drop_table("fertilizer_history")
    op.drop_table("escalation_contacts")
    op.drop_table("crop_stage_calendars")
    op.drop_table("crop_images")
    op.drop_table("chat_sessions")
    op.drop_table("farms")
    op.drop_table("users")
