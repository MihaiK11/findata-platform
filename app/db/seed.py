import asyncio
from datetime import datetime, timezone
from app.db.database import connect_db, get_database


DATA_SOURCES = [
    {
        "source_id": "QUOTEMEDIA/PRICES",
        "name": "Nasdaq QuoteMedia Prices",
        "description": "End of day OHLCV price data for US equities",
        "url": "https://data.nasdaq.com/databases/QMP",
        "provider": "Nasdaq",
        "valid_from": datetime.now(timezone.utc),
        "is_deleted": False,
    },
    {
        "source_id": "YAHOO/FINANCE",
        "name": "Yahoo Finance",
        "description": "Free market data for stocks, crypto and ETFs",
        "url": "https://finance.yahoo.com",
        "provider": "Yahoo",
        "valid_from": datetime.now(timezone.utc),
        "is_deleted": False,
    },
]


async def seed_data_sources():
    db = get_database()
    for source in DATA_SOURCES:
        existing = await db.data_sources.find_one(
            {"source_id": source["source_id"]}
        )
        if not existing:
            await db.data_sources.insert_one(source)
            print(f"✓ Inserted data source: {source['source_id']}")
        else:
            print(f"✓ Data source already exists: {source['source_id']}")


async def main():
    await connect_db()
    await seed_data_sources()


if __name__ == "__main__":
    asyncio.run(main())