from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Numeric, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CropImage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "crop_images"
    __table_args__ = (
        CheckConstraint(
            "latitude IS NULL OR latitude BETWEEN -90 AND 90",
            name="latitude_range",
        ),
        CheckConstraint(
            "longitude IS NULL OR longitude BETWEEN -180 AND 180",
            name="longitude_range",
        ),
        CheckConstraint(
            "file_size_bytes IS NULL OR file_size_bytes >= 0",
            name="file_size_bytes_non_negative",
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
    image_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    storage_key: Mapped[Optional[str]] = mapped_column(String(512), unique=True)
    content_type: Mapped[Optional[str]] = mapped_column(String(100))
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger)
    captured_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    latitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 6))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    image_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    farm: Mapped["Farm"] = relationship(back_populates="crop_images")
    uploaded_by: Mapped[Optional["User"]] = relationship(back_populates="crop_images")
    diagnoses: Mapped[list["Diagnosis"]] = relationship(
        back_populates="crop_image",
        passive_deletes=True,
    )


class Diagnosis(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "diagnoses"
    __table_args__ = (
        CheckConstraint(
            "confidence IS NULL OR confidence BETWEEN 0 AND 1",
            name="confidence_range",
        ),
    )

    farm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("farms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    crop_image_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crop_images.id", ondelete="SET NULL"),
        index=True,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
        index=True,
    )
    diagnosis_type: Mapped[Optional[str]] = mapped_column(String(100))
    crop_name: Mapped[Optional[str]] = mapped_column(String(100))
    condition_name: Mapped[Optional[str]] = mapped_column(String(255))
    confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4))
    severity: Mapped[Optional[str]] = mapped_column(String(32), index=True)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    recommendations: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    raw_result: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    diagnosed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    farm: Mapped["Farm"] = relationship(back_populates="diagnoses")
    crop_image: Mapped[Optional["CropImage"]] = relationship(back_populates="diagnoses")
    requested_by: Mapped[Optional["User"]] = relationship(back_populates="diagnoses")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="diagnosis")
    escalations: Mapped[list["Escalation"]] = relationship(back_populates="diagnosis")
