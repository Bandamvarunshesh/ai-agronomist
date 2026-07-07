from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import CheckConstraint, Date, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class FertilizerHistory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fertilizer_history"
    __table_args__ = (
        CheckConstraint(
            "quantity IS NULL OR quantity >= 0",
            name="quantity_non_negative",
        ),
    )

    farm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("farms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    applied_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    fertilizer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    fertilizer_type: Mapped[Optional[str]] = mapped_column(String(100))
    quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    unit: Mapped[Optional[str]] = mapped_column(String(32))
    application_method: Mapped[Optional[str]] = mapped_column(String(100))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    farm: Mapped["Farm"] = relationship(back_populates="fertilizer_history")
