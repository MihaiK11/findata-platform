"""Financial assistant MCP server — wraps Findata FastAPI tools for Claude / Cursor."""

from __future__ import annotations

import os

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("financial-assistant")

BASE_URL = os.getenv("FINDATA_API_URL", "http://127.0.0.1:8000").rstrip("/")


async def _fetch(method: str, path: str, **kwargs) -> dict | list:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(method, f"{BASE_URL}{path}", **kwargs)
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_asset_list() -> dict:
    """Return all tracked assets in the data warehouse."""
    return await _fetch("GET", "/assets")


@mcp.tool()
async def get_latest_price(symbol: str) -> dict:
    """Return the latest OHLCV price for a symbol."""
    return await _fetch("GET", f"/prices/latest/{symbol.upper()}")


@mcp.tool()
async def get_asset_price_history(symbol: str, start_date: str, end_date: str) -> dict:
    """Return historical time-series for a symbol between ISO dates (YYYY-MM-DD)."""
    return await _fetch(
        "GET",
        "/prices/history",
        params={
            "symbol": symbol.upper(),
            "start_date": start_date,
            "end_date": end_date,
        },
    )


@mcp.tool()
async def compare_assets(symbols: list[str], start_date: str, end_date: str) -> dict:
    """Compare multiple symbols over a date range."""
    return await _fetch(
        "POST",
        "/compare",
        json={
            "symbols": [s.upper() for s in symbols],
            "start_date": start_date,
            "end_date": end_date,
        },
    )


@mcp.tool()
async def get_asset_stats(symbol: str, window: str = "90d") -> dict:
    """Return analytics stats (mean, min, max, MAs, trend) for a symbol and window (e.g. 30d, 90d)."""
    return await _fetch(
        "GET",
        "/analytics/stats",
        params={"symbol": symbol.upper(), "window": window},
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
