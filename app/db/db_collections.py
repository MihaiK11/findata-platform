from datetime import datetime, timezone
from app.db.database import get_database


async def init_collections():
    db = get_database()

    existing = await db.list_collection_names()

    # --- assets collection ---
    if "assets" not in existing:
        await db.create_collection("assets")
        print("✓ Created 'assets' collection")
    else:
        print("✓ 'assets' collection already exists")

    await db.assets.create_index(
        [("symbol", 1), ("valid_from", -1)]
    )
    await db.assets.create_index("instrument_class")
    await db.assets.create_index("region")
    print("✓ Indexes created for 'assets'")

    # --- data_sources collection ---
    if "data_sources" not in existing:
        await db.create_collection("data_sources")
        print("✓ Created 'data_sources' collection")
    else:
        print("✓ 'data_sources' collection already exists")

    await db.data_sources.create_index(
        [("source_id", 1), ("valid_from", -1)],
        unique=True
    )
    print("✓ Indexes created for 'data_sources'")

    # --- time_series collection ---
    if "time_series" not in existing:
        await db.create_collection("time_series")
        print("✓ Created 'time_series' collection")
    else:
        print("✓ 'time_series' collection already exists")

    await db.time_series.create_index(
        [("symbol", 1), ("data_source_id", 1), ("date", -1)]
    )
    await db.time_series.create_index("date")
    print("✓ Indexes created for 'time_series'")

    print("\n✓ All collections and indexes ready")


async def get_current_asset(symbol: str):
    """
    Temporal rule: always return the latest non-deleted version of an asset.
    """
    db = get_database()
    return await db.assets.find_one(
        {"symbol": symbol, "is_deleted": False},
        sort=[("valid_from", -1)]
    )


async def insert_asset_version(asset_doc: dict):
    """
    Temporal rule: never update — always insert a new version.
    """
    db = get_database()
    await db.assets.insert_one(asset_doc)


async def delete_asset_temporal(symbol: str):
    """
    Temporal rule: never hard delete — insert a marker document instead.
    """
    db = get_database()
    current = await get_current_asset(symbol)
    if current:
        marker = {**current, "is_deleted": True, "valid_from": datetime.now(timezone.utc)}
        marker.pop("_id", None)  # remove MongoDB id so it inserts as new doc
        await db.assets.insert_one(marker)
        print(f"✓ Asset {symbol} marked as deleted")