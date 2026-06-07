from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from streamlit_app.services.api_client import APIClient, APIClientError


# ─────────────────────────────────────────────
# SYSTEM PROMPT (HUMANIZED + CONTROLLED)
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """
You are a friendly and intelligent financial assistant.

CORE RULES:
- Never invent or guess financial data.
- Always use tools for any financial information.
- If data is missing, say:
  "I don't have enough data in the system to answer that."

STYLE:
- Speak like a helpful human analyst, not a machine.
- Be natural and conversational.
- Explain what numbers mean in simple terms.
- Avoid raw dumps of data.
- Keep responses short and clear.
- Prefer explanations over lists.
- When appropriate, add context like trends or meaning.

BEHAVIOR:
- If user greets you, respond naturally and briefly.
- If user asks follow-up questions, assume continuity.
- If comparing assets, highlight the best performer in plain language.
- If showing trends, describe direction (up, down, stable).
- Avoid technical jargon unless user asks for it.

EXAMPLES:

Bad:
"AAPL latest price 210.32"

Good:
"AAPL is currently trading around 210.32 based on the latest data."

Bad:
"trend: UP"

Good:
"AAPL has been trending upward, showing positive momentum."

Bad:
"volatility: 0.12"

Good:
"The stock has shown moderate volatility over this period."
"""


# ─────────────────────────────────────────────
# DATE HELPERS
# ─────────────────────────────────────────────
def _iso_date(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def default_range(days: int = 30) -> tuple[str, str]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    return _iso_date(start), _iso_date(end)


# ─────────────────────────────────────────────
# TOOL DEFINITIONS
# ─────────────────────────────────────────────
OPENAI_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_asset_list",
            "description": "Get list of all available financial assets.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_latest_price",
            "description": "Get the latest price of a stock symbol.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock ticker like AAPL, MSFT, TSLA"
                    }
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_asset_price_history",
            "description": "Get historical price data for a stock between two dates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                },
                "required": ["symbol", "start_date", "end_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_assets",
            "description": "Compare multiple stocks over a time range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbols": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                },
                "required": ["symbols", "start_date", "end_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_asset_stats",
            "description": "Get analytics like trend, volatility, and averages.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "window": {
                        "type": "string",
                        "description": "Time window like 30d, 90d, 1y"
                    },
                },
                "required": ["symbol"],
            },
        },
    },
]

ANTHROPIC_TOOL_DEFINITIONS = OPENAI_TOOL_DEFINITIONS


# ─────────────────────────────────────────────
# CLIENT
# ─────────────────────────────────────────────
class AssistantToolClient:
    """HTTP client for backend financial tools."""

    def __init__(self, base_url: str) -> None:
        self._api = APIClient(base_url)

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._api._request(path, params=params)

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._api.base_url}{path}"
        with httpx.Client(timeout=self._api.timeout) as client:
            response = client.post(url, json=body)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise APIClientError("expected JSON object")
            return payload

    def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "get_asset_list":
            return self._get("/assets")

        if name == "get_latest_price":
            return self._get(f"/prices/latest/{arguments['symbol'].upper()}")

        if name == "get_asset_price_history":
            return self._get(
                "/prices/history",
                {
                    "symbol": arguments["symbol"].upper(),
                    "start_date": arguments["start_date"],
                    "end_date": arguments["end_date"],
                },
            )

        if name == "compare_assets":
            return self._post(
                "/compare",
                {
                    "symbols": [s.upper() for s in arguments["symbols"]],
                    "start_date": arguments["start_date"],
                    "end_date": arguments["end_date"],
                },
            )

        if name == "get_asset_stats":
            params: dict[str, Any] = {"symbol": arguments["symbol"].upper()}
            if arguments.get("window"):
                params["window"] = arguments["window"]
            return self._get("/analytics/stats", params)

        raise APIClientError(f"Unknown tool: {name}")


# ─────────────────────────────────────────────
# TOOL EXECUTION
# ─────────────────────────────────────────────
def execute_tool(client: AssistantToolClient, name: str, arguments: dict[str, Any]) -> str:
    try:
        result = client.execute(name, arguments)
        return json.dumps(result, default=str)
    except APIClientError as exc:
        return json.dumps({"error": str(exc)})
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text
        return json.dumps({"error": detail or str(exc)})