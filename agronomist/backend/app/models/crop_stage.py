from __future__ import annotations

import uuid
from datetime import date
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Crop(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "crops"
    __table_args__ = (
        UniqueConstraint("normalized_name", name="uq_crops_normalized_name"),
        CheckConstraint(
            "duration_days IS NULL OR duration_days > 0",
            name="duration_days_positive",
        ),
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(100))
    duration_days: Mapped[Optional[int]] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
        index=True,
    )
    crop_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    stages: Mapped[list["CropStage"]] = relationship(
        back_populates="crop",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="CropStage.stage_order",
    )


class CropStage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "crop_stages"
    __table_args__ = (
        UniqueConstraint("crop_id", "stage_name", name="uq_crop_stages_crop_stage"),
        UniqueConstraint("crop_id", "stage_order", name="uq_crop_stages_crop_order"),
        CheckConstraint("stage_order >= 0", name="stage_order_non_negative"),
        CheckConstraint("start_day >= 0", name="start_day_non_negative"),
        CheckConstraint("end_day >= start_day", name="end_day_after_start_day"),
    )

    crop_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crops.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage_name: Mapped[str] = mapped_column(String(100), nullable=False)
    stage_order: Mapped[int] = mapped_column(Integer, nullable=False)
    start_day: Mapped[int] = mapped_column(Integer, nullable=False)
    end_day: Mapped[int] = mapped_column(Integer, nullable=False)
    important_actions: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    risk_factors: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    ai_recommendations: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    stage_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    crop: Mapped["Crop"] = relationship(back_populates="stages")


class CropStageCalendar(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "crop_stage_calendars"
    __table_args__ = (
        UniqueConstraint(
            "farm_id",
            "crop_name",
            "stage_name",
            name="uq_crop_stage_calendars_farm_crop_stage",
        ),
        CheckConstraint(
            "stage_order IS NULL OR stage_order >= 0",
            name="stage_order_non_negative",
        ),
        CheckConstraint(
            "expected_start_day IS NULL OR expected_start_day >= 0",
            name="expected_start_day_non_negative",
        ),
        CheckConstraint(
            "expected_end_day IS NULL OR expected_end_day >= 0",
            name="expected_end_day_non_negative",
        ),
    )

    farm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("farms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    crop_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    stage_name: Mapped[str] = mapped_column(String(100), nullable=False)
    stage_order: Mapped[Optional[int]] = mapped_column(Integer)
    start_date: Mapped[Optional[date]] = mapped_column(Date)
    end_date: Mapped[Optional[date]] = mapped_column(Date)
    expected_start_day: Mapped[Optional[int]] = mapped_column(Integer)
    expected_end_day: Mapped[Optional[int]] = mapped_column(Integer)
    tasks: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    recommendations: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )

    farm: Mapped["Farm"] = relationship(back_populates="crop_stage_calendars")
