from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import CheckConstraint, Date, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Farm(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "farms"
    __table_args__ = (
        CheckConstraint(
            "land_size_acres >= 0",
            name="land_size_acres_non_negative",
        ),
        CheckConstraint(
            "latitude IS NULL OR latitude BETWEEN -90 AND 90",
            name="ck_farms_latitude_range",
        ),
        CheckConstraint(
            "longitude IS NULL OR longitude BETWEEN -180 AND 180",
            name="ck_farms_longitude_range",
        ),
        CheckConstraint(
            "location_source IN ('current_location', 'map_selection', 'manual')",
            name="ck_farms_location_source",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    farm_name: Mapped[str] = mapped_column(String(255), nullable=False)
    crop: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    village: Mapped[str] = mapped_column(String(100), nullable=False)
    locality: Mapped[Optional[str]] = mapped_column(String(100))
    district: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    latitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 6))
    formatted_address: Mapped[Optional[str]] = mapped_column(String(500))
    country: Mapped[Optional[str]] = mapped_column(String(100))
    postal_code: Mapped[Optional[str]] = mapped_column(String(20))
    location_source: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    soil_type: Mapped[Optional[str]] = mapped_column(String(100))
    land_size_acres: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    irrigation_type: Mapped[Optional[str]] = mapped_column(String(100))
    sowing_date: Mapped[Optional[date]] = mapped_column(Date)

    owner: Mapped["User"] = relationship(back_populates="farms")
    fertilizer_history: Mapped[list["FertilizerHistory"]] = relationship(
        back_populates="farm",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    crop_images: Mapped[list["CropImage"]] = relationship(
        back_populates="farm",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    diagnoses: Mapped[list["Diagnosis"]] = relationship(
        back_populates="farm",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    chat_sessions: Mapped[list["ChatSession"]] = relationship(back_populates="farm")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="farm")
    timeline_events: Mapped[list["TimelineEvent"]] = relationship(
        back_populates="farm",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    recommendations: Mapped[list["FarmRecommendation"]] = relationship(
        back_populates="farm",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    crop_stage_calendars: Mapped[list["CropStageCalendar"]] = relationship(
        back_populates="farm",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    escalation_contacts: Mapped[list["EscalationContact"]] = relationship(
        back_populates="farm"
    )
    escalations: Mapped[list["Escalation"]] = relationship(
        back_populates="farm",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
