from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class TimeSeriesPoint(BaseModel):
    symbol: str
    data_source_id: str   # references DataSource.source_id
    date: datetime

    # common OHLCV fields
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[float] = None

    # adjusted fields
    adj_open: Optional[float] = None
    adj_high: Optional[float] = None
    adj_low: Optional[float] = None
    adj_close: Optional[float] = None
    adj_volume: Optional[float] = None

    # extra fields for heterogeneous instruments
    extra_attributes: dict = {}

    # temporal fields
    valid_from: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_deleted: bool = False