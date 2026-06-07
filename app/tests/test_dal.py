import pytest

from app.db.db_collections import (
    insert_asset_version,
    get_current_asset,
    delete_asset_temporal
)

@pytest.mark.asyncio
async def test_insert_asset_version():

    asset = {
        "symbol": "TEST",
        "is_deleted": False
    }

    await insert_asset_version(asset)

    current = await get_current_asset("TEST")

    assert current is not None


@pytest.mark.asyncio
async def test_latest_version_semantics():

    await insert_asset_version({
        "symbol": "AAPL",
        "version": 1,
        "is_deleted": False
    })

    await insert_asset_version({
        "symbol": "AAPL",
        "version": 2,
        "is_deleted": False
    })

    current = await get_current_asset("AAPL")

    assert current["version"] == 2


@pytest.mark.asyncio
async def test_delete_asset_temporal():

    await delete_asset_temporal("AAPL")

    current = await get_current_asset("AAPL")

    assert current is None