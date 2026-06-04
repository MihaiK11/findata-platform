"""Ingest assets and OHLCV time series into MongoDB.

Nasdaq Data Link free sample for QUOTEMEDIA/PRICES only includes a few tickers (e.g. AAPL).
Other symbols return empty unless you have a paid subscription — we fall back to Yahoo Finance.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import datetime, timezone

import nasdaqdatalink
import pandas as pd
import yfinance as yf

from app.config import settings
from app.db.database import connect_db, get_database

logger = logging.getLogger(__name__)

NASDAQ_SOURCE = "QUOTEMEDIA/PRICES"
YAHOO_SOURCE = "YAHOO/FINANCE"

nasdaqdatalink.ApiConfig.api_key = settings.nasdaq_api_key

DEFAULT_SYMBOLS = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]


def _normalize_nasdaq_frame(data: pd.DataFrame, symbol: str) -> pd.DataFrame:
    if data.empty:
        return data
    frame = data.copy()
    if "ticker" in frame.columns:
        frame = frame.drop(columns=["ticker"])
    if "date" in frame.columns:
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["symbol"] = symbol
    return frame


def fetch_from_nasdaq(symbol: str, *, per_page: int = 500) -> pd.DataFrame:
    print(f"  Nasdaq ({NASDAQ_SOURCE})…")
    data = nasdaqdatalink.get_table(
        "QUOTEMEDIA/PRICES",
        ticker=symbol,
        qopts={"per_page": per_page},
        paginate=True,
    )
    return _normalize_nasdaq_frame(data, symbol)


def fetch_from_yahoo(symbol: str, *, period: str = "2y") -> pd.DataFrame:
    print(f"  Yahoo Finance fallback ({YAHOO_SOURCE})…")
    raw = yf.download(symbol, period=period, progress=False, auto_adjust=False)
    if raw.empty:
        ticker = yf.Ticker(symbol)
        raw = ticker.history(period=period, auto_adjust=False)
    if raw.empty:
        return raw

    frame = raw.reset_index()
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = [col[0] if isinstance(col, tuple) else col for col in frame.columns]

    rename = {
        "Date": "date",
        "Datetime": "date",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
    }
    frame = frame.rename(columns={k: v for k, v in rename.items() if k in frame.columns})
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce", utc=True).dt.tz_convert(None)
    frame["symbol"] = symbol
    keep = [c for c in ["symbol", "date", "open", "high", "low", "close", "volume"] if c in frame.columns]
    return frame[keep].dropna(subset=["date"])


def fetch_asset(symbol: str, *, yahoo_period: str = "2y", prefer_yahoo: bool = False) -> tuple[pd.DataFrame, str]:
    symbol = symbol.upper().strip()
    print(f"\n{'=' * 40}\nFetching: {symbol}")

    if prefer_yahoo:
        frame = fetch_from_yahoo(symbol, period=yahoo_period)
        source = YAHOO_SOURCE
    else:
        frame = fetch_from_nasdaq(symbol)
        source = NASDAQ_SOURCE
        if frame.empty:
            print(
                f"  Nasdaq returned no rows for {symbol}. "
                "Free QUOTEMEDIA/PRICES sample is limited (mostly AAPL). Trying Yahoo…"
            )
            frame = fetch_from_yahoo(symbol, period=yahoo_period)
            source = YAHOO_SOURCE

    print(f"  Rows: {len(frame)}  Source: {source}")
    if not frame.empty:
        print(frame.tail(3).to_string(index=False))
    return frame, source


async def save_asset(symbol: str, data: pd.DataFrame, data_source: str) -> int:
    if data.empty:
        print(f"  SKIP {symbol}: no price rows — asset not updated.")
        return 0

    db = get_database()
    symbol = symbol.upper().strip()

    asset_doc = {
        "symbol": symbol,
        "instrument_class": "stock",
        "description": f"{symbol} stock",
        "region": "US",
        "valid_from": datetime.now(timezone.utc),
        "is_deleted": False,
        "data_source": data_source,
        "data_source_id": data_source,
    }

    await db.assets.update_one({"symbol": symbol}, {"$set": asset_doc}, upsert=True)
    print(f"  Asset {symbol} saved (source={data_source})")

    inserted = 0
    for row in data.to_dict(orient="records"):
        date_val = row.get("date")
        if hasattr(date_val, "to_pydatetime"):
            date_val = date_val.to_pydatetime()
        if date_val is None:
            continue

        ts_doc = {
            "symbol": symbol,
            "data_source": data_source,
            "data_source_id": data_source,
            "date": date_val,
            "valid_from": datetime.now(timezone.utc),
            "is_deleted": False,
            "open": row.get("open"),
            "high": row.get("high"),
            "low": row.get("low"),
            "close": row.get("close"),
            "volume": row.get("volume"),
        }

        result = await db.time_series.update_one(
            {"symbol": symbol, "date": date_val, "data_source": data_source},
            {"$setOnInsert": ts_doc},
            upsert=True,
        )
        if result.upserted_id is not None:
            inserted += 1

    print(f"  {inserted} new time-series rows for {symbol} ({len(data)} rows in fetch)")
    return inserted


async def ingest_symbols(
    symbols: list[str],
    *,
    yahoo_period: str = "2y",
    prefer_yahoo: bool = False,
) -> None:
    await connect_db()
    total = 0
    for symbol in symbols:
        frame, source = fetch_asset(symbol, yahoo_period=yahoo_period, prefer_yahoo=prefer_yahoo)
        total += await save_asset(symbol, frame, source)
    print(f"\nDone — {total} new time-series documents inserted.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest OHLCV data into MongoDB")
    parser.add_argument(
        "symbols",
        nargs="*",
        default=DEFAULT_SYMBOLS,
        help=f"Ticker symbols (default: {' '.join(DEFAULT_SYMBOLS)})",
    )
    parser.add_argument(
        "--yahoo-only",
        action="store_true",
        help="Skip Nasdaq and load from Yahoo Finance only",
    )
    parser.add_argument(
        "--period",
        default="2y",
        help="Yahoo history period when using fallback (default: 2y)",
    )
    return parser.parse_args()


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    args = parse_args()
    await ingest_symbols(
        [s.upper() for s in args.symbols],
        yahoo_period=args.period,
        prefer_yahoo=args.yahoo_only,
    )


if __name__ == "__main__":
    asyncio.run(main())
