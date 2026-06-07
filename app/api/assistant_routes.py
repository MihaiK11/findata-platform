from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services import market_data

router = APIRouter(tags=["assistant"])


class CompareRequest(BaseModel):
    symbols: list[str] = Field(..., min_length=1)
    start_date: str
    end_date: str


@router.get("/assets")
async def get_asset_list() -> dict[str, Any]:
    assets = await market_data.list_assets()
    return {"count": len(assets), "assets": assets}


@router.get("/prices/latest/{symbol}")
async def get_latest_price(symbol: str) -> dict[str, Any]:
    result = await market_data.get_latest_price(symbol)
    if not result.get("found"):
        raise HTTPException(status_code=404, detail=result.get("message", "Not found"))
    return result


@router.get("/prices/history")
async def get_asset_price_history(
    symbol: str = Query(...),
    start_date: str = Query(..., description="ISO date, e.g. 2025-01-01"),
    end_date: str = Query(..., description="ISO date, e.g. 2025-06-01"),
) -> dict[str, Any]:
    result = await market_data.get_price_history(symbol, start_date, end_date)
    if result["count"] == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No historical data for '{symbol.upper()}' between {start_date} and {end_date}",
        )
    return result


@router.post("/compare")
async def compare_assets(body: CompareRequest) -> dict[str, Any]:
    result = await market_data.compare_assets(body.symbols, body.start_date, body.end_date)
    if all(item.get("count", 0) == 0 for item in result["comparisons"]):
        raise HTTPException(status_code=404, detail="No data for any symbol in the requested range.")
    return result


@router.get("/analytics/stats")
async def get_asset_stats(
    symbol: str = Query(...),
    window: str = Query(default="90d", description="e.g. 30d, 90d, 1y"),
) -> dict[str, Any]:
    result = await market_data.get_asset_stats(symbol, window)
    if not result.get("found"):
        raise HTTPException(status_code=404, detail=result.get("message", "Not found"))
    return result
