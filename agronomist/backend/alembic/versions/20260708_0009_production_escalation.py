"""production human escalation

Revision ID: 20260708_0009
Revises: 20260708_0008
Create Date: 2026-07-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260708_0009"
down_revision = "20260708_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("escalation_contacts", "user_id", nullable=True)
    op.add_column(
        "escalation_contacts",
        sa.Column(
            "contact_type",
            sa.String(length=32),
            server_default=sa.text("'agronomist'"),
            nullable=False,
        ),
    )
    op.add_column(
        "escalation_contacts",
        sa.Column("district", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "escalation_contacts",
        sa.Column("state", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "escalation_contacts",
        sa.Column(
            "contact_priority",
            sa.Integer(),
            server_default=sa.text("100"),
            nullable=False,
        ),
    )
    op.add_column(
        "escalation_contacts",
        sa.Column(
            "is_fallback",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "escalation_contacts",
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.add_column(
        "escalation_contacts",
        sa.Column(
            "service_area",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        op.f("ck_escalation_contacts_escalation_contact_type_allowed"),
        "escalation_contacts",
        "contact_type IN ('kvk', 'agronomist', 'govt_extension', 'vet', 'emergency')",
    )
    op.create_check_constraint(
        op.f("ck_escalation_contacts_escalation_contact_priority_non_negative"),
        "escalation_contacts",
        "contact_priority >= 0",
    )
    op.create_index(
        op.f("ix_escalation_contacts_contact_type"),
        "escalation_contacts",
        ["contact_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_escalation_contacts_district"),
        "escalation_contacts",
        ["district"],
        unique=False,
    )
    op.create_index(
        op.f("ix_escalation_contacts_state"),
        "escalation_contacts",
        ["state"],
        unique=False,
    )
    op.create_index(
        op.f("ix_escalation_contacts_contact_priority"),
        "escalation_contacts",
        ["contact_priority"],
        unique=False,
    )
    op.create_index(
        op.f("ix_escalation_contacts_is_fallback"),
        "escalation_contacts",
        ["is_fallback"],
        unique=False,
    )

    op.add_column(
        "escalations",
        sa.Column("chat_session_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "escalations",
        sa.Column(
            "escalation_type",
            sa.String(length=32),
            server_default=sa.text("'manual'"),
            nullable=False,
        ),
    )
    op.add_column(
        "escalations",
        sa.Column("contact_type_requested", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "escalations",
        sa.Column(
            "routing_status",
            sa.String(length=32),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
    )
    op.add_column(
        "escalations",
        sa.Column("routing_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "escalations",
        sa.Column(
            "fallback_used",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "escalations",
        sa.Column(
            "contact_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.create_foreign_key(
        op.f("fk_escalations_chat_session_id_chat_sessions"),
        "escalations",
        "chat_sessions",
        ["chat_session_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        op.f("ck_escalations_escalation_status_allowed"),
        "escalations",
        "status IN ('open', 'routed', 'in_progress', 'resolved', 'closed', 'failed')",
    )
    op.create_check_constraint(
        op.f("ck_escalations_escalation_priority_allowed"),
        "escalations",
        "priority IN ('low', 'normal', 'high', 'urgent')",
    )
    op.create_check_constraint(
        op.f("ck_escalations_escalation_type_allowed"),
        "escalations",
        "escalation_type IN ('diagnosis', 'chat', 'manual')",
    )
    op.create_index(
        op.f("ix_escalations_chat_session_id"),
        "escalations",
        ["chat_session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_escalations_escalation_type"),
        "escalations",
        ["escalation_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_escalations_contact_type_requested"),
        "escalations",
        ["contact_type_requested"],
        unique=False,
    )
    op.create_index(
        op.f("ix_escalations_routing_status"),
        "escalations",
        ["routing_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_escalations_fallback_used"),
        "escalations",
        ["fallback_used"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_escalations_fallback_used"), table_name="escalations")
    op.drop_index(op.f("ix_escalations_routing_status"), table_name="escalations")
    op.drop_index(
        op.f("ix_escalations_contact_type_requested"),
        table_name="escalations",
    )
    op.drop_index(op.f("ix_escalations_escalation_type"), table_name="escalations")
    op.drop_index(op.f("ix_escalations_chat_session_id"), table_name="escalations")
    op.drop_constraint(
        op.f("ck_escalations_escalation_type_allowed"),
        "escalations",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_escalations_escalation_priority_allowed"),
        "escalations",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_escalations_escalation_status_allowed"),
        "escalations",
        type_="check",
    )
    op.drop_constraint(
        op.f("fk_escalations_chat_session_id_chat_sessions"),
        "escalations",
        type_="foreignkey",
    )
    op.drop_column("escalations", "contact_snapshot")
    op.drop_column("escalations", "fallback_used")
    op.drop_column("escalations", "routing_reason")
    op.drop_column("escalations", "routing_status")
    op.drop_column("escalations", "contact_type_requested")
    op.drop_column("escalations", "escalation_type")
    op.drop_column("escalations", "chat_session_id")

    op.drop_index(
        op.f("ix_escalation_contacts_is_fallback"),
        table_name="escalation_contacts",
    )
    op.drop_index(
        op.f("ix_escalation_contacts_contact_priority"),
        table_name="escalation_contacts",
    )
    op.drop_index(
        op.f("ix_escalation_contacts_state"),
        table_name="escalation_contacts",
    )
    op.drop_index(
        op.f("ix_escalation_contacts_district"),
        table_name="escalation_contacts",
    )
    op.drop_index(
        op.f("ix_escalation_contacts_contact_type"),
        table_name="escalation_contacts",
    )
    op.drop_constraint(
        op.f("ck_escalation_contacts_escalation_contact_priority_non_negative"),
        "escalation_contacts",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_escalation_contacts_escalation_contact_type_allowed"),
        "escalation_contacts",
        type_="check",
    )
    op.drop_column("escalation_contacts", "service_area")
    op.drop_column("escalation_contacts", "notes")
    op.drop_column("escalation_contacts", "is_fallback")
    op.drop_column("escalation_contacts", "contact_priority")
    op.drop_column("escalation_contacts", "state")
    op.drop_column("escalation_contacts", "district")
    op.drop_column("escalation_contacts", "contact_type")
    op.alter_column("escalation_contacts", "user_id", nullable=False)
