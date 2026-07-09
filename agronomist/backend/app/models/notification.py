from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Notification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    farm_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("farms.id", ondelete="SET NULL"),
        index=True,
    )
    diagnosis_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("diagnoses.id", ondelete="SET NULL"),
        index=True,
    )
    notification_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="normal",
        server_default=text("'normal'"),
        index=True,
    )
    channel: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="in_app",
        server_default=text("'in_app'"),
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        index=True,
    )
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    scheduled_for: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    source: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="system",
        server_default=text("'system'"),
        index=True,
    )
    dedupe_key: Mapped[Optional[str]] = mapped_column(
        String(255),
        unique=True,
        index=True,
    )
    deep_link: Mapped[Optional[str]] = mapped_column(String(1024))
    push_title: Mapped[Optional[str]] = mapped_column(String(255))
    push_body: Mapped[Optional[str]] = mapped_column(Text)
    push_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    delivery_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
        index=True,
    )
    delivery_error: Mapped[Optional[str]] = mapped_column(Text)

    user: Mapped["User"] = relationship(back_populates="notifications")
    farm: Mapped[Optional["Farm"]] = relationship(back_populates="notifications")
    diagnosis: Mapped[Optional["Diagnosis"]] = relationship(back_populates="notifications")


class NotificationPreference(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notification_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    notifications_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    in_app_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    push_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    email_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    sms_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    enabled_types: Mapped[dict[str, bool]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    quiet_hours_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    quiet_hours_start: Mapped[Optional[str]] = mapped_column(String(5))
    quiet_hours_end: Mapped[Optional[str]] = mapped_column(String(5))
    timezone: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="UTC",
        server_default=text("'UTC'"),
    )
    push_token: Mapped[Optional[str]] = mapped_column(String(512))
    push_platform: Mapped[Optional[str]] = mapped_column(String(32))
    push_provider: Mapped[Optional[str]] = mapped_column(String(32))
    device_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    user: Mapped["User"] = relationship(back_populates="notification_preference")
