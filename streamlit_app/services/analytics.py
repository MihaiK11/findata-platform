from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(slots=True)
class AnalyticsSummary:
    latest_price: float | None
    min_price: float | None
    max_price: float | None
    mean_price: float | None
    median_price: float | None
    std_dev: float | None
    average_return: float | None
    volatility: float | None
    trend: str
    forecast_next_close: float | None
    moving_averages: dict[str, float | None]


def _clean_frame(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    if "date" in frame.columns:
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        frame = frame.dropna(subset=["date"])
        frame = frame.sort_values("date")
    if "close" not in frame.columns:
        raise ValueError("close column is required")
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    frame = frame.dropna(subset=["close"])
    if frame.empty:
        raise ValueError("no valid close values")
    return frame


def add_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    frame = _clean_frame(df)
    frame["ma5"] = frame["close"].rolling(5, min_periods=1).mean()
    frame["ma20"] = frame["close"].rolling(20, min_periods=1).mean()
    frame["ma50"] = frame["close"].rolling(50, min_periods=1).mean()
    return frame


def detect_trend(df: pd.DataFrame) -> str:
    frame = add_moving_averages(df)
    latest = frame.iloc[-1]
    if latest["ma5"] > latest["ma20"] > latest["ma50"]:
        return "Bullish"
    if latest["ma5"] < latest["ma20"] < latest["ma50"]:
        return "Bearish"
    return "Sideways"


def forecast_next_close(df: pd.DataFrame) -> float | None:
    frame = _clean_frame(df)
    close = frame["close"].astype(float).to_numpy()
    if close.size < 2:
        return float(close[-1])
    x = np.arange(close.size, dtype=float)
    slope, intercept = np.polyfit(x, close, 1)
    return float(slope * close.size + intercept)


def summarize(df: pd.DataFrame) -> AnalyticsSummary:
    frame = _clean_frame(df)
    close = frame["close"].astype(float)
    returns = close.pct_change().dropna()
    latest = float(close.iloc[-1])
    ma_frame = add_moving_averages(frame)
    ma_latest = ma_frame.iloc[-1]

    return AnalyticsSummary(
        latest_price=latest,
        min_price=float(close.min()),
        max_price=float(close.max()),
        mean_price=float(close.mean()),
        median_price=float(close.median()),
        std_dev=float(close.std(ddof=1)) if len(close) > 1 else 0.0,
        average_return=float(returns.mean()) if not returns.empty else 0.0,
        volatility=float(returns.std(ddof=1)) if len(returns) > 1 else 0.0,
        trend=detect_trend(frame),
        forecast_next_close=forecast_next_close(frame),
        moving_averages={
            "ma5": float(ma_latest["ma5"]),
            "ma20": float(ma_latest["ma20"]),
            "ma50": float(ma_latest["ma50"]),
        },
    )

