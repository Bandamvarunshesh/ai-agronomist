from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "email IS NOT NULL OR phone_number IS NOT NULL",
            name="contact_present",
        ),
    )

    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String(32), unique=True, index=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    profile_picture_url: Mapped[Optional[str]] = mapped_column(String(1024))
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    preferred_language: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="en",
        server_default=text("'en'"),
    )
    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="farmer",
        server_default=text("'farmer'"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    default_state: Mapped[Optional[str]] = mapped_column(String(100))
    default_district: Mapped[Optional[str]] = mapped_column(String(100))
    default_farm_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("farms.id", ondelete="SET NULL"),
        index=True,
    )
    account_settings: Mapped[dict[str, Any]] = mapped_column(
        "settings",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    farms: Mapped[list["Farm"]] = relationship(
        foreign_keys="Farm.user_id",
        back_populates="owner",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    crop_images: Mapped[list["CropImage"]] = relationship(back_populates="uploaded_by")
    diagnoses: Mapped[list["Diagnosis"]] = relationship(back_populates="requested_by")
    chat_sessions: Mapped[list["ChatSession"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    chat_messages: Mapped[list["ChatMessage"]] = relationship(back_populates="user")
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    notification_preference: Mapped[Optional["NotificationPreference"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    timeline_events: Mapped[list["TimelineEvent"]] = relationship(back_populates="user")
    farm_recommendations: Mapped[list["FarmRecommendation"]] = relationship(
        back_populates="user",
    )
    escalation_contacts: Mapped[list["EscalationContact"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    escalations: Mapped[list["Escalation"]] = relationship(back_populates="user")
