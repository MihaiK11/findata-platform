from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query

from app.db.database import get_database
from app.db.db_collections import get_current_asset

router = APIRouter(prefix="/api/v1", tags=["queries"])


def _serialize(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items() if key != "_id"}
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
    pipeline.extend(
        [
            {"$sort": {"symbol": 1, "valid_from": -1}},
            {"$group": {"_id": "$symbol", "doc": {"$first": "$$ROOT"}}},
            {"$replaceRoot": {"newRoot": "$doc"}},
            {"$sort": {"symbol": 1}},
        ]
    )
    return [doc async for doc in db.assets.aggregate(pipeline)]


async def _latest_documents_by_key(collection_name: str, key_field: str) -> list[dict]:
    db = get_database()
    pipeline = [
        {"$match": {"is_deleted": False}},
        {"$sort": {key_field: 1, "valid_from": -1}},
        {"$group": {"_id": f"${key_field}", "doc": {"$first": "$$ROOT"}}},
        {"$replaceRoot": {"newRoot": "$doc"}},
        {"$sort": {key_field: 1}},
    ]
    return [doc async for doc in db[collection_name].aggregate(pipeline)]


# Q1: current asset by symbol
@router.get("/q1/assets/{symbol}")
async def q1_current_asset(symbol: str):
    asset = await get_current_asset(symbol)
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset not found for symbol '{symbol}'")
    return {"query": "Q1", "data": _normalize_doc(asset)}


# Q2: latest assets with optional filters
@router.get("/q2/assets")
async def q2_latest_assets(
    instrument_class: Optional[str] = Query(default=None),
    region: Optional[str] = Query(default=None),
):
    assets = await _latest_assets_pipeline({"is_deleted": False})
    if instrument_class:
        assets = [asset for asset in assets if asset.get("instrument_class") == instrument_class]
    if region:
        assets = [asset for asset in assets if asset.get("region") == region]
    return {"query": "Q2", "count": len(assets), "data": _serialize(assets)}


# Q3: data sources, optionally filtered by source_id
@router.get("/q3/data-sources")
async def q3_data_sources(source_id: Optional[str] = Query(default=None)):
    docs = await _latest_documents_by_key("data_sources", "source_id")
    if source_id:
        docs = [doc for doc in docs if doc.get("source_id") == source_id]
    if source_id and not docs:
        raise HTTPException(status_code=404, detail=f"Data source not found for source_id '{source_id}'")
    return {"query": "Q3", "count": len(docs), "data": _serialize(docs)}


# Q4: time series for a symbol over an optional date range
@router.get("/q4/time-series/{symbol}")
async def q4_time_series(
    symbol: str,
    data_source_id: Optional[str] = Query(default=None),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
):
    db = get_database()
    query: dict[str, Any] = {"symbol": symbol, "is_deleted": False}
    if data_source_id:
        query["$or"] = [{"data_source_id": data_source_id}, {"data_source": data_source_id}]
    if start_date or end_date:
        date_query: dict[str, Any] = {}
        if start_date:
            date_query["$gte"] = start_date
        if end_date:
            date_query["$lte"] = end_date
        query["date"] = date_query

    docs = [
        doc
        async for doc in db.time_series.find(query).sort("date", 1).limit(limit)
    ]
    return {"query": "Q4", "symbol": symbol, "count": len(docs), "data": _serialize(docs)}


# Q5: latest time-series snapshot per symbol for a source
@router.get("/q5/latest-time-series")
async def q5_latest_time_series(
    data_source_id: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
):
    db = get_database()
    pipeline: list[dict[str, Any]] = [{"$match": {"is_deleted": False}}]
    if data_source_id:
        pipeline[0]["$match"]["$or"] = [
            {"data_source_id": data_source_id},
            {"data_source": data_source_id},
        ]
    pipeline.extend(
        [
            {"$sort": {"symbol": 1, "date": -1}},
            {"$group": {"_id": "$symbol", "doc": {"$first": "$$ROOT"}}},
            {"$replaceRoot": {"newRoot": "$doc"}},
            {"$sort": {"symbol": 1}},
            {"$limit": limit},
        ]
    )
    docs = [doc async for doc in db.time_series.aggregate(pipeline)]
    return {"query": "Q5", "count": len(docs), "data": _serialize(docs)}
