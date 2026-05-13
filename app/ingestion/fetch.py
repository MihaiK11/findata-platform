import nasdaqdatalink
import asyncio
from datetime import datetime, timezone
from app.config import settings
from app.db.database import connect_db, get_database

nasdaqdatalink.ApiConfig.api_key = settings.nasdaq_api_key


def fetch_asset(symbol: str):
    print(f"\n{'='*40}")
    print(f"Fetching data for: {symbol}")

    data = nasdaqdatalink.get_table("QUOTEMEDIA/PRICES", ticker=symbol, qopts={"per_page": 5})

    print(f"Columns: {list(data.columns)}")
    print(f"\nLast 5 days:")
    print(data)

    return data


async def save_asset(symbol: str, data):
    db = get_database()

    # Save asset metadata into 'assets' collection
    asset_doc = {
        "symbol": symbol,
        "instrument_class": "stock",
        "description": f"{symbol} stock",
        "region": "US",
        "valid_from": datetime.now(timezone.utc),
        "is_deleted": False,
        "data_source": "QUOTEMEDIA/PRICES",
    }

    # Upsert — insert if not exists, skip if already there
    await db.assets.update_one(
        {"symbol": symbol},
        {"$setOnInsert": asset_doc},
        upsert=True
    )
    print(f"✓ Asset {symbol} saved to 'assets' collection")

    # Save each row as a time series document
    records = data.to_dict(orient="records")
    for row in records:
        # Convert date to datetime if needed
        if hasattr(row.get("date"), "to_pydatetime"):
            row["date"] = row["date"].to_pydatetime()

        ts_doc = {
            "symbol": symbol,
            "data_source": "QUOTEMEDIA/PRICES",
            "valid_from": datetime.now(timezone.utc),
            "is_deleted": False,
            **row  # spread all columns (open, high, low, close, volume etc.)
        }

        # Temporal rule — never update, only insert if not already there
        await db.time_series.update_one(
            {"symbol": symbol, "date": row["date"], "data_source": "QUOTEMEDIA/PRICES"},
            {"$setOnInsert": ts_doc},
            upsert=True
        )

    print(f"✓ {len(records)} time series records saved for {symbol}")


async def main():
    await connect_db()

    symbols = ["AAPL", "MSFT"]
    for symbol in symbols:
        data = fetch_asset(symbol)
        await save_asset(symbol, data)

    print("\n✓ All done — check MongoDB Atlas to verify")


if __name__ == "__main__":
    asyncio.run(main())