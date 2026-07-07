from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, String, text
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

    farms: Mapped[list["Farm"]] = relationship(
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
    timeline_events: Mapped[list["TimelineEvent"]] = relationship(back_populates="user")
    escalation_contacts: Mapped[list["EscalationContact"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    escalations: Mapped[list["Escalation"]] = relationship(back_populates="user")
