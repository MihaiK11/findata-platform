from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional

class Asset(BaseModel):
    symbol: str
    instrument_class: str  # stock, bond, crypto, commodity, index, futures, metals
    description: str
    region: str            # US, Europe, China, Africa etc.
    currency: Optional[str] = None
    exchange: Optional[str] = None
    extra_attributes: dict = {}

    valid_from: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_deleted: bool = False