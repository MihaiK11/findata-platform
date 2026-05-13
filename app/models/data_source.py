from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class DataSource(BaseModel):
    source_id: str        # e.g. "QUOTEMEDIA/PRICES"
    name: str             # e.g. "Nasdaq QuoteMedia"
    description: str
    url: Optional[str] = None
    provider: str         # e.g. "Nasdaq", "Bloomberg", "Yahoo"

    # temporal fields
    valid_from: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_deleted: bool = False