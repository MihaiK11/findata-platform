from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query

from app.db.database import get_database
from app.db.db_collections import get_current_asset

router = APIRouter(prefix="/api/v1", tags=["queries"])


# ----------------------------
# Helpers
# ----------------------------
def _serialize(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {k: _serialize(v) for k, v in value.items() if k != "_id"}
    return value


def _normalize_doc(doc: Optional[dict]) -> Optional[dict]:
    if not doc:
        return None
    return _serialize(doc)


async def _latest_assets_pipeline(match: dict | None = None) -> list[dict]:
    db = get_database()
    pipeline = []

    if match:
        pipeline.append({"$match": match})

    pipeline.extend([
        {"$sort": {"symbol": 1, "valid_from": -1}},
        {"$group": {"_id": "$symbol", "doc": {"$first": "$$ROOT"}}},
        {"$replaceRoot": {"newRoot": "$doc"}},
        {"$sort": {"symbol": 1}},
    ])

    return [doc async for doc in db.assets.aggregate(pipeline)]


# ----------------------------
# Q1 - current asset
# ----------------------------
@router.get("/q1/assets/{symbol}")
async def q1_current_asset(symbol: str):
    asset = await get_current_asset(symbol)

    if not asset:
        raise HTTPException(404, f"Asset not found for symbol '{symbol}'")

    return {"query": "Q1", "data": _normalize_doc(asset)}


# ----------------------------
# Q2 - latest assets
# ----------------------------
@router.get("/q2/assets")
async def q2_latest_assets(
    instrument_class: Optional[str] = None,
    region: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
):
    assets = await _latest_assets_pipeline({"is_deleted": False})

    if instrument_class:
        assets = [a for a in assets if a.get("instrument_class") == instrument_class]

    if region:
        assets = [a for a in assets if a.get("region") == region]

    total = len(assets)
    return {
        "query": "Q2",
        "skip": skip,
        "limit": limit,
        "total": total,
        "count": len(assets[skip:skip + limit]),
        "data": _serialize(assets[skip:skip + limit]),
    }


# ----------------------------
# Q4 - time series (core endpoint)
# ----------------------------
@router.get("/q4/time-series/{symbol}")
async def q4_time_series(
    symbol: str,
    data_source_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
):
    db = get_database()

    query: dict[str, Any] = {
        "symbol": symbol,
        "is_deleted": False,
    }

    if data_source_id:
        query["$or"] = [
            {"data_source_id": data_source_id},
            {"data_source": data_source_id},
        ]

    if start_date or end_date:
        query["date"] = {}
        if start_date:
            query["date"]["$gte"] = start_date
        if end_date:
            query["date"]["$lte"] = end_date

    docs = [
        doc async for doc in db.time_series.find(query)
        .sort("date", 1)
        .limit(limit)
    ]

    return {
        "query": "Q4",
        "symbol": symbol,
        "count": len(docs),
        "data": _serialize(docs),
    }


# ----------------------------
# 🔥 NEW: Backward-compatible endpoint for your frontend
# /prices/history?symbol=AAPL
# ----------------------------
@router.get("/prices/history")
async def prices_history(
    symbol: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    data_source_id: Optional[str] = None,
    limit: int = 100,
):
    return await q4_time_series(
        symbol=symbol,
        data_source_id=data_source_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )


# ----------------------------
# Q5 - latest time series
# ----------------------------
@router.get("/q5/latest-time-series")
async def q5_latest_time_series(
    data_source_id: Optional[str] = None,
    limit: int = 100,
):
    db = get_database()

    match = {"is_deleted": False}

    if data_source_id:
        match["$or"] = [
            {"data_source_id": data_source_id},
            {"data_source": data_source_id},
        ]

    pipeline = [
        {"$match": match},
        {"$sort": {"symbol": 1, "date": -1}},
        {"$group": {"_id": "$symbol", "doc": {"$first": "$$ROOT"}}},
        {"$replaceRoot": {"newRoot": "$doc"}},
        {"$sort": {"symbol": 1}},
        {"$limit": limit},
    ]

    docs = [doc async for doc in db.time_series.aggregate(pipeline)]

    return {
        "query": "Q5",
        "count": len(docs),
        "data": _serialize(docs),
    }