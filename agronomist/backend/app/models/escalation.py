from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer
from sqlalchemy import String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class EscalationContact(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "escalation_contacts"
    __table_args__ = (
        CheckConstraint(
            "contact_type IN ('kvk', 'agronomist', 'govt_extension', 'vet', 'emergency')",
            name="escalation_contact_type_allowed",
        ),
        CheckConstraint(
            "contact_priority >= 0",
            name="escalation_contact_priority_non_negative",
        ),
    )

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    farm_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("farms.id", ondelete="SET NULL"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    role: Mapped[Optional[str]] = mapped_column(String(100))
    organization: Mapped[Optional[str]] = mapped_column(String(255))
    district: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String(32))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    preferred_channel: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="phone",
        server_default=text("'phone'"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
        index=True,
    )
    contact_priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
        server_default=text("100"),
        index=True,
    )
    is_fallback: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        index=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text)
    service_area: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    user: Mapped[Optional["User"]] = relationship(back_populates="escalation_contacts")
    farm: Mapped[Optional["Farm"]] = relationship(back_populates="escalation_contacts")
    escalations: Mapped[list["Escalation"]] = relationship(back_populates="contact")


class Escalation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "escalations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'routed', 'in_progress', 'resolved', 'closed', 'failed')",
            name="escalation_status_allowed",
        ),
        CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent')",
            name="escalation_priority_allowed",
        ),
        CheckConstraint(
            "escalation_type IN ('diagnosis', 'chat', 'manual')",
            name="escalation_type_allowed",
        ),
    )

    farm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("farms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )
    diagnosis_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("diagnoses.id", ondelete="SET NULL"),
        index=True,
    )
    chat_session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="SET NULL"),
        index=True,
    )
    contact_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("escalation_contacts.id", ondelete="SET NULL"),
        index=True,
    )
    escalation_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="manual",
        server_default=text("'manual'"),
        index=True,
    )
    contact_type_requested: Mapped[Optional[str]] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="open",
        server_default=text("'open'"),
        index=True,
    )
    priority: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="normal",
        server_default=text("'normal'"),
        index=True,
    )
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text)
    routing_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
        index=True,
    )
    routing_reason: Mapped[Optional[str]] = mapped_column(Text)
    fallback_used: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        index=True,
    )
    contact_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    escalated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    escalation_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    farm: Mapped["Farm"] = relationship(back_populates="escalations")
    user: Mapped[Optional["User"]] = relationship(back_populates="escalations")
    diagnosis: Mapped[Optional["Diagnosis"]] = relationship(back_populates="escalations")
    chat_session: Mapped[Optional["ChatSession"]] = relationship()
    contact: Mapped[Optional["EscalationContact"]] = relationship(back_populates="escalations")
