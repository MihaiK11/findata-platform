from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional

class TimeSeriesPoint(BaseModel):
    symbol: str
    data_source_id: str
    date: datetime

    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[float] = None

    adj_open: Optional[float] = None
    adj_high: Optional[float] = None
    adj_low: Optional[float] = None
    adj_close: Optional[float] = None
    adj_volume: Optional[float] = None

    extra_attributes: dict = {}

    valid_from: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_deleted: bool = False