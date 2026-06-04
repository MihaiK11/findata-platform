from __future__ import annotations

import logging

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.db.database import get_database
from app.analytics.analytics_service import summarize_timeseries

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["analytics"])


class MovingAverages(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ma5: float | None = None
    ma20: float | None = None
    ma50: float | None = None


class AnalyticsResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    symbol: str
    latest_price: float | None = None
    min_price: float | None = None
    max_price: float | None = None
    mean_price: float | None = None
    median_price: float | None = None
    std_dev: float | None = None
    volatility: float | None = None
    trend: str
    forecast_next_close: float | None = None
    moving_averages: MovingAverages = Field(default_factory=MovingAverages)
    average_return: float | None = None
    stats: dict[str, float | None] = Field(default_factory=dict)


@router.get("/{symbol}", response_model=AnalyticsResponse)
async def get_analytics(symbol: str) -> AnalyticsResponse:
    db = get_database()
    docs = [doc async for doc in db.time_series.find({"symbol": symbol, "is_deleted": False}).sort("date", 1)]
    if not docs:
        logger.warning("No time-series rows for symbol=%s", symbol)
        raise HTTPException(status_code=404, detail=f"No time-series data found for symbol '{symbol}'")

    logger.info("Analytics request for symbol=%s rows=%s", symbol, len(docs))
    frame = pd.DataFrame(docs)
    result = summarize_timeseries(symbol, frame)
    return AnalyticsResponse(
        symbol=result.symbol,
        latest_price=result.latest_price,
        min_price=result.min_price,
        max_price=result.max_price,
        mean_price=result.mean_price,
        median_price=result.median_price,
        std_dev=result.std_dev,
        volatility=result.volatility,
        trend=result.trend,
        forecast_next_close=result.forecast_next_close,
        moving_averages=MovingAverages(**result.moving_averages),
        average_return=result.average_return,
        stats=result.stats,
    )

