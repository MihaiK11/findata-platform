from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AnalyticsResult:
    symbol: str
    latest_price: float | None
    min_price: float | None
    max_price: float | None
    mean_price: float | None
    median_price: float | None
    std_dev: float | None
    volatility: float | None
    trend: str
    forecast_next_close: float | None
    moving_averages: dict[str, float | None]
    average_return: float | None
    stats: dict[str, float | None]
    dataframe: pd.DataFrame


def _close_series(df: pd.DataFrame) -> pd.Series:
    if "close" not in df.columns:
        raise ValueError("time-series data must include a 'close' column")
    series = pd.to_numeric(df["close"], errors="coerce").dropna()
    if series.empty:
        raise ValueError("no valid close prices found")
    return series


def add_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result = result.sort_values("date")
    result["ma5"] = result["close"].rolling(window=5, min_periods=1).mean()
    result["ma20"] = result["close"].rolling(window=20, min_periods=1).mean()
    result["ma50"] = result["close"].rolling(window=50, min_periods=1).mean()
    return result


def compute_trend(df: pd.DataFrame) -> str:
    enriched = add_moving_averages(df)
    latest = enriched.iloc[-1]
    ma5 = float(latest["ma5"])
    ma20 = float(latest["ma20"])
    ma50 = float(latest["ma50"])

    if ma5 > ma20 > ma50:
        return "Bullish"
    if ma5 < ma20 < ma50:
        return "Bearish"
    return "Sideways"


def forecast_next_close(df: pd.DataFrame) -> float | None:
    close = _close_series(df)
    if len(close) < 2:
        return float(close.iloc[-1])

    x = np.arange(len(close), dtype=float)
    y = close.to_numpy(dtype=float)
    slope, intercept = np.polyfit(x, y, deg=1)
    next_value = slope * (len(close)) + intercept
    return float(next_value)


def summarize_timeseries(symbol: str, df: pd.DataFrame) -> AnalyticsResult:
    if df.empty:
        raise ValueError("time-series dataframe is empty")

    logger.info("Computing analytics for %s (%s rows)", symbol, len(df))

    work = df.copy()
    if "date" in work.columns:
        work["date"] = pd.to_datetime(work["date"], errors="coerce")
        work = work.dropna(subset=["date"])
    work = work.sort_values("date")

    close = _close_series(work)
    latest_price = float(close.iloc[-1])
    min_price = float(close.min())
    max_price = float(close.max())
    mean_price = float(close.mean())
    median_price = float(close.median())
    std_dev = float(close.std(ddof=1)) if len(close) > 1 else 0.0

    daily_returns = close.pct_change().dropna()
    average_return = float(daily_returns.mean()) if not daily_returns.empty else 0.0
    volatility = float(daily_returns.std(ddof=1)) if len(daily_returns) > 1 else 0.0

    enriched = add_moving_averages(work)
    latest = enriched.iloc[-1]
    ma5 = float(latest["ma5"])
    ma20 = float(latest["ma20"])
    ma50 = float(latest["ma50"])
    trend = compute_trend(work)
    forecast = forecast_next_close(work)

    return AnalyticsResult(
        symbol=symbol,
        latest_price=latest_price,
        min_price=min_price,
        max_price=max_price,
        mean_price=mean_price,
        median_price=median_price,
        std_dev=std_dev,
        volatility=volatility,
        trend=trend,
        forecast_next_close=forecast,
        moving_averages={"ma5": ma5, "ma20": ma20, "ma50": ma50},
        average_return=average_return,
        stats={
            "min_price": min_price,
            "max_price": max_price,
            "mean_price": mean_price,
            "median_price": median_price,
            "std_dev": std_dev,
            "latest_price": latest_price,
        },
        dataframe=enriched,
    )

