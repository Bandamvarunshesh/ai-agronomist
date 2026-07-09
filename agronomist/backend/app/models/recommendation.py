from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class FarmRecommendation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "farm_recommendations"
    __table_args__ = (
        CheckConstraint(
            "farm_health_score BETWEEN 0 AND 100",
            name="farm_health_score_range",
        ),
        CheckConstraint(
            "confidence_score BETWEEN 0 AND 1",
            name="farm_recommendation_confidence_score_range",
        ),
        CheckConstraint(
            "risk_level IN ('low', 'moderate', 'high', 'critical')",
            name="farm_recommendation_risk_level_allowed",
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
    farm_health_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    prioritized_recommendations: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    daily_action_plan: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    weekly_summary: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    context_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    raw_model_output: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    farm: Mapped["Farm"] = relationship(back_populates="recommendations")
    user: Mapped[Optional["User"]] = relationship(back_populates="farm_recommendations")
