from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd

from app.analytics.analytics_service import add_moving_averages, summarize_timeseries
from app.db.database import get_database


# ─────────────────────────────────────────────
# TIME HELPERS
# ─────────────────────────────────────────────
def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def parse_window(window: str | None, *, end: datetime | None = None) -> tuple[datetime, datetime]:
    end_dt = end or _utc_now()

    if not window:
        return end_dt - timedelta(days=90), end_dt

    window = window.strip().lower()

    match = re.fullmatch(r"(\d+)(d|w|m|y)", window)
    if match:
        value = int(match.group(1))
        unit = match.group(2)
        days = value * {"d": 1, "w": 7, "m": 30, "y": 365}[unit]
        return end_dt - timedelta(days=days), end_dt

    if "|" in window:
        start_s, end_s = window.split("|", 1)
        return _parse_iso(start_s), _parse_iso(end_s)

    return end_dt - timedelta(days=90), end_dt


# ─────────────────────────────────────────────
# SERIALIZATION
# ─────────────────────────────────────────────
def _serialize_doc(doc: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in doc.items():
        if k == "_id":
            continue
        out[k] = v.isoformat() if isinstance(v, datetime) else v
    return out


# ─────────────────────────────────────────────
# ASSETS
# ─────────────────────────────────────────────
async def list_assets() -> list[dict[str, Any]]:
    db = get_database()

    pipeline = [
        {"$match": {"is_deleted": False}},
        {"$sort": {"symbol": 1, "valid_from": -1}},
        {"$group": {"_id": "$symbol", "doc": {"$first": "$$ROOT"}}},
        {"$replaceRoot": {"newRoot": "$doc"}},
        {"$sort": {"symbol": 1}},
    ]

    docs = [d async for d in db.assets.aggregate(pipeline)]

    return [
        {
            "symbol": d.get("symbol"),
            "name": d.get("description") or d.get("name"),
        }
        for d in docs
        if d.get("symbol")
    ]


# ─────────────────────────────────────────────
# TIMESERIES CORE
# ─────────────────────────────────────────────
async def fetch_timeseries(
    symbol: str,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    *,
    limit: int = 1000,
) -> list[dict[str, Any]]:
    symbol = symbol.upper().strip()
    db = get_database()

    query: dict[str, Any] = {"symbol": symbol, "is_deleted": False}

    if start_date or end_date:
        q: dict[str, Any] = {}
        if start_date:
            q["$gte"] = start_date
        if end_date:
            q["$lte"] = end_date
        query["date"] = q

    docs = (
        db.time_series.find(query)
        .sort("date", 1)
        .limit(limit)
    )

    return [_serialize_doc(d) async for d in docs]


# ─────────────────────────────────────────────
# LATEST PRICE (FIXED UX)
# ─────────────────────────────────────────────
async def get_latest_price(symbol: str) -> dict[str, Any]:
    symbol = symbol.upper().strip()
    db = get_database()

    doc = await db.time_series.find_one(
        {"symbol": symbol, "is_deleted": False},
        sort=[("date", -1)],
    )

    if not doc:
        return {
            "symbol": symbol,
            "found": False,
            "message": f"No data found for {symbol}. Try another ticker.",
        }

    d = _serialize_doc(doc)

    return {
        "symbol": symbol,
        "found": True,
        "date": d.get("date"),
        "close": d.get("close"),
    }


# ─────────────────────────────────────────────
# HISTORY (FIXED: NEVER MISLEADING EMPTY)
# ─────────────────────────────────────────────
async def get_price_history(symbol: str, start_date: str, end_date: str) -> dict[str, Any]:
    symbol = symbol.upper().strip()

    start = _parse_iso(start_date)
    end = _parse_iso(end_date)

    rows = await fetch_timeseries(symbol, start, end)

    # ✅ FIX: never silently return empty dataset
    if not rows:
        return {
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date,
            "count": 0,
            "data": [],
            "summary": {
                "message": f"No historical data found for {symbol} in this period."
            },
        }

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date")

    close = pd.to_numeric(df["close"], errors="coerce").dropna()

    if close.empty:
        return {
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date,
            "count": 0,
            "data": [],
            "summary": {"message": "Data exists but prices are incomplete."},
        }

    first, last = float(close.iloc[0]), float(close.iloc[-1])

    return {
        "symbol": symbol,
        "start_date": start_date,
        "end_date": end_date,
        "count": len(rows),
        "data": rows,
        "summary": {
            "start_close": first,
            "end_close": last,
            "pct_change": round((last / first - 1) * 100, 2) if first else None,
            "min_close": float(close.min()),
            "max_close": float(close.max()),
        },
    }


# ─────────────────────────────────────────────
# COMPARE (SIMPLIFIED + STABLE)
# ─────────────────────────────────────────────
async def compare_assets(symbols: list[str], start_date: str, end_date: str) -> dict[str, Any]:
    symbols = [s.upper().strip() for s in symbols if s]

    results = []
    for s in symbols:
        h = await get_price_history(s, start_date, end_date)
        summary = h.get("summary") or {}

        results.append({
            "symbol": s,
            "pct_change": summary.get("pct_change"),
        })

    return {
        "symbols": symbols,
        "start_date": start_date,
        "end_date": end_date,
        "comparisons": results,
    }


# ─────────────────────────────────────────────
# STATS (UNCHANGED BUT SAFE)
# ─────────────────────────────────────────────
async def get_asset_stats(symbol: str, window: str = "90d") -> dict[str, Any]:
    symbol = symbol.upper().strip()

    start, end = parse_window(window)
    rows = await fetch_timeseries(symbol, start, end)

    if not rows:
        return {
            "symbol": symbol,
            "window": window,
            "found": False,
            "message": f"No data found for {symbol} in this window.",
        }

    df = pd.DataFrame(rows)
    result = summarize_timeseries(symbol, df)
    enriched = add_moving_averages(df)

    return {
        "symbol": symbol,
        "window": window,
        "found": True,
        "latest_price": result.latest_price,
        "mean_price": result.mean_price,
        "min_price": result.min_price,
        "max_price": result.max_price,
        "trend": result.trend,
        "volatility": result.volatility,
        "moving_averages": result.moving_averages,
        "points": len(enriched),
    }