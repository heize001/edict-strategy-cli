from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Bar(BaseModel):
    """A minimal OHLCV bar model (extend as needed)."""

    ts: datetime = Field(..., description="Bar timestamp (UTC recommended)")
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None
