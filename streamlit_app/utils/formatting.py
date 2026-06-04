from __future__ import annotations

from typing import Any

import pandas as pd


def normalize_records(records: list[dict[str, Any]]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame()
    frame = pd.DataFrame(records)
    if "date" in frame.columns:
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        frame = frame.dropna(subset=["date"]).sort_values("date")
    for col in ("open", "high", "low", "close", "volume"):
        if col in frame.columns:
            frame[col] = pd.to_numeric(frame[col], errors="coerce")
    return frame


def page_slice(frame: pd.DataFrame, page: int, page_size: int) -> pd.DataFrame:
    start = max(page - 1, 0) * page_size
    return frame.iloc[start : start + page_size]


def assets_to_browser_frame(assets: list[dict[str, Any]]) -> pd.DataFrame:
    rows = [
        {
            "Symbol": asset.get("symbol", ""),
            "Name": asset.get("description") or asset.get("name") or asset.get("symbol", ""),
            "Asset type": asset.get("instrument_class", ""),
            "Data source": asset.get("data_source_id") or asset.get("data_source", ""),
        }
        for asset in assets
    ]
    return pd.DataFrame(rows)


def format_currency(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    return f"{float(value):,.2f}"


def format_percent(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    return f"{float(value):.4f}"


def trend_badge(trend: str) -> str:
    normalized = (trend or "Sideways").strip().title()
    if normalized not in {"Bullish", "Bearish", "Sideways"}:
        return normalized
    return normalized
