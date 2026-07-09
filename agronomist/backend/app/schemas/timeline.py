from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class TimelineEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    farm_id: uuid.UUID
    user_id: Optional[uuid.UUID]
    event_type: str
    title: str
    description: Optional[str]
    event_date: date
    source: str
    payload: dict[str, Any]
    created_at: datetime
    updated_at: datetime
