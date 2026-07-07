from __future__ import annotations

import uuid
from datetime import date
from typing import Any, Optional

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


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
