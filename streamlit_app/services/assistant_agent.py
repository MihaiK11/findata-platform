from __future__ import annotations

import json
import re
from typing import Any

from streamlit_app.services.assistant_tools import (
    OPENAI_TOOL_DEFINITIONS,
    SYSTEM_PROMPT,
    AssistantToolClient,
    default_range,
    execute_tool,
)

# ─────────────────────────────────────────────
# GREETINGS
# ─────────────────────────────────────────────
GREETINGS = {
    "hi", "hello", "hey",
    "good morning", "good afternoon", "good evening",
}

# ─────────────────────────────────────────────
# STOP WORDS
# ─────────────────────────────────────────────
_STOP_WORDS: frozenset[str] = frozenset({
    "A","I","AM","AN","AS","AT","BE","BY","DO","GO","HI","IF","IN","IS","IT",
    "ME","MY","NO","OF","ON","OR","SO","TO","UP","US","WE",
    "ALL","AND","ARE","CAN","DAY","DID","FOR","GET","GOT","HAD","HAS","HIM",
    "HIS","HOW","ITS","LET","MAY","NOT","NOW","OLD","OUR","OUT","OWN","PUT",
    "RUN","SAY","SEE","SET","SHE","THE","TOO","TWO","USE","WAS","WAY","WHO",
    "WHY","YOU",
    "CHART","PRICE","TREND","STATS","DATA","DAYS","WEEK","MONTH",
    "HISTORY","LATEST","COMPARE","ANALYSIS","ASSET","ASSETS",
})


# ─────────────────────────────────────────────
# SYMBOL EXTRACTION
# ─────────────────────────────────────────────
def _extract_symbol(text: str) -> str | None:
    for match in re.finditer(r"\b([A-Z]{1,5})\b", text.upper()):
        candidate = match.group(1)
        if candidate not in _STOP_WORDS:
            return candidate
    return None


def _get_valid_symbols(client: AssistantToolClient) -> set[str]:
    """Fetch valid tickers from backend."""
    try:
        data = client.execute("get_asset_list", {})
        return {a["symbol"].upper() for a in data.get("assets", [])}
    except Exception:
        return set()


# ─────────────────────────────────────────────
# RULE-BASED ROUTER
# ─────────────────────────────────────────────
def _rule_based_tool_call(question: str) -> tuple[str, dict[str, Any]] | None:
    q = question.lower()
    start, end = default_range(30)

    symbol = _extract_symbol(question)

    if "compare" in q:
        symbols = re.findall(r"\b[A-Z]{1,5}\b", question.upper())
        symbols = [s for s in symbols if s not in _STOP_WORDS]

        if len(symbols) >= 2:
            return "compare_assets", {
                "symbols": symbols[:5],
                "start_date": start,
                "end_date": end,
            }

    if not symbol:
        if any(x in q for x in ["list", "assets", "symbols"]):
            return "get_asset_list", {}
        return None

    if any(x in q for x in ["latest", "price now", "current"]):
        return "get_latest_price", {"symbol": symbol}

    if any(x in q for x in ["trend", "history", "chart"]):
        return "get_asset_price_history", {
            "symbol": symbol,
            "start_date": start,
            "end_date": end,
        }

    if any(x in q for x in ["stats", "analysis", "volatility"]):
        return "get_asset_stats", {"symbol": symbol, "window": "30d"}

    return "get_asset_stats", {"symbol": symbol, "window": "30d"}


# ─────────────────────────────────────────────
# OPENAI AGENT
# ─────────────────────────────────────────────
def run_openai_agent(
    client: AssistantToolClient,
    api_key: str,
    question: str,
    *,
    model: str = "gpt-4o",
    max_turns: int = 5,
) -> tuple[str, list[dict[str, Any]]]:

    from openai import OpenAI

    openai_client = OpenAI(api_key=api_key)

    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT +
            "\n\nStyle rules:\n"
            "- Respond like a helpful financial assistant\n"
            "- Keep answers simple and natural\n"
            "- No JSON, no raw tool output\n"
        },
        {"role": "user", "content": question},
    ]

    trace: list[dict[str, Any]] = []

    for _ in range(max_turns):
        response = openai_client.chat.completions.create(
            model=model,
            tools=OPENAI_TOOL_DEFINITIONS,
            tool_choice="auto",
            messages=messages,
        )

        msg = response.choices[0].message
        messages.append(msg.model_dump(exclude_unset=True))

        if not msg.tool_calls:
            return (msg.content or "").strip(), trace

        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments or "{}")

            raw = execute_tool(client, tc.function.name, args)

            trace.append({
                "tool": tc.function.name,
                "input": args,
                "output": raw,
            })

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": raw,
            })

    return "I couldn't complete your request.", trace


# ─────────────────────────────────────────────
# MAIN ENTRY
# ─────────────────────────────────────────────
def answer_question(
    client: AssistantToolClient,
    question: str,
    *,
    api_key: str | None = None,
) -> tuple[str, list[dict[str, Any]], dict[str, Any] | None]:

    chart_payload: dict[str, Any] | None = None
    clean = question.lower().strip()

    # ───────────────
    # GREETINGS
    # ───────────────
    if any(g in clean for g in GREETINGS):
        return (
            "Hi 👋 I can help you explore stocks, prices, trends, and comparisons. What would you like to check?",
            [],
            None,
        )

    if clean in {"thanks", "thank you"}:
        return ("You're welcome 🙂", [], None)

    if clean in {"bye", "goodbye"}:
        return ("Goodbye 👋", [], None)

    # ───────────────
    # OPENAI MODE
    # ───────────────
    if api_key:
        try:
            answer, trace = run_openai_agent(client, api_key, question)
        except Exception as e:
            return (f"Error processing request: {str(e)}", [], None)

    # ───────────────
    # FALLBACK MODE
    # ───────────────
    else:
        routed = _rule_based_tool_call(question)

        if not routed:
            try:
                assets = client.execute("get_asset_list", {}).get("assets", [])[:5]
                symbols = ", ".join([a["symbol"] for a in assets]) or "AAPL, MSFT"
            except Exception:
                symbols = "AAPL, MSFT, TSLA"

            return (
                f"I couldn't find that. Try one of these: {symbols} 🙂",
                [],
                None,
            )

        tool_name, args = routed
        raw = execute_tool(client, tool_name, args)

        trace = [{
            "tool": tool_name,
            "input": args,
            "output": raw,
        }]

        payload = json.loads(raw)

        # ───────────────
        # HUMAN RESPONSES
        # ───────────────
        if tool_name == "get_latest_price":
            answer = (
                f"{payload['symbol']} is trading around {payload['close']} "
                f"(latest data from {payload['date']})."
            )

        elif tool_name == "get_asset_stats":
            answer = (
                f"{payload['symbol']} shows a {payload.get('trend', 'stable')} trend over the last {payload['window']}. "
                f"Latest price is {payload.get('latest_price')}."
            )

        elif tool_name == "get_asset_price_history":
            s = payload.get("summary", {})
            answer = (
                f"{payload['symbol']} moved from {s.get('start_close')} to {s.get('end_close')} "
                f"over the selected period ({payload['start_date']} → {payload['end_date']})."
            )

        elif tool_name == "compare_assets":
            comps = payload.get("comparisons", [])
            if comps:
                best = max(comps, key=lambda x: x.get("pct_change", 0))
                answer = (
                    "Comparison results:\n" +
                    "\n".join([f"• {c['symbol']}: {c['pct_change']}%" for c in comps]) +
                    f"\n\nBest performer: {best['symbol']}"
                )
            else:
                answer = "No comparison data available."

        elif tool_name == "get_asset_list":
            assets = payload.get("assets", [])
            answer = "Tracked assets: " + ", ".join([a["symbol"] for a in assets[:10]])

        else:
            answer = "Data retrieved, but I couldn't format it clearly."

    # ───────────────
    # CHART
    # ───────────────
    for item in trace:
        if item["tool"] != "get_asset_price_history":
            continue

        try:
            payload = json.loads(item["output"])
        except Exception:
            continue

        rows = payload.get("data") or []
        if rows:
            chart_payload = {
                "symbol": payload.get("symbol"),
                "start_date": payload.get("start_date"),
                "end_date": payload.get("end_date"),
                "rows": rows,
            }
            break

    return answer, trace, chart_payload