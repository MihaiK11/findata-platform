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

GREETINGS = {
    "hi", "hello", "hey",
    "good morning", "good afternoon", "good evening",
}

_STOP_WORDS = frozenset({
    "A","I","AM","AN","AS","AT","BE","BY","DO","GO","HI","IF","IN","IS","IT",
    "ME","MY","NO","OF","ON","OR","SO","TO","UP","US","WE",
    "ALL","AND","ARE","CAN","DAY","DID","FOR","GET","GOT","HAD","HAS","HIM",
    "HIS","HOW","ITS","LET","MAY","NOT","NOW","OLD","OUR","OUT","OWN","PUT",
    "RUN","SAY","SEE","SET","SHE","THE","TOO","TWO","USE","WAS","WAY","WHO",
    "WHY","YOU",
    "CHART","PRICE","TREND","STATS","DATA","DAYS","WEEK","MONTH",
    "HISTORY","LATEST","COMPARE","ANALYSIS","ASSET","ASSETS",
})


def _extract_symbol(text: str) -> str | None:
    for m in re.finditer(r"\b([A-Z]{1,5})\b", text.upper()):
        s = m.group(1)
        if s not in _STOP_WORDS:
            return s
    return None


def _safe_json_loads(s: str) -> dict[str, Any]:
    try:
        return json.loads(s or "{}")
    except Exception:
        return {}


def _rule_based_tool_call(question: str):
    q = question.lower()
    start, end = default_range(30)

    symbol = _extract_symbol(question)

    if "compare" in q:
        symbols = [s for s in re.findall(r"\b[A-Z]{1,5}\b", question.upper()) if s not in _STOP_WORDS]
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

    if any(x in q for x in ["latest", "current", "price now"]):
        return "get_latest_price", {"symbol": symbol}

    if any(x in q for x in ["history", "trend", "chart"]):
        return "get_asset_price_history", {
            "symbol": symbol,
            "start_date": start,
            "end_date": end,
        }

    if any(x in q for x in ["stats", "analysis", "volatility"]):
        return "get_asset_stats", {"symbol": symbol, "window": "30d"}

    return "get_asset_stats", {"symbol": symbol, "window": "30d"}


def run_openai_agent(
    client: AssistantToolClient,
    api_key: str,
    question: str,
    *,
    model: str = "gpt-4o",
    max_turns: int = 5,
):
    from openai import OpenAI

    openai_client = OpenAI(api_key=api_key)

    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT + "\n\nRespond like a helpful financial assistant.",
        },
        {"role": "user", "content": question},
    ]

    trace = []

    for _ in range(max_turns):
        resp = openai_client.chat.completions.create(
            model=model,
            tools=OPENAI_TOOL_DEFINITIONS,
            tool_choice="auto",
            messages=messages,
        )

        msg = resp.choices[0].message

        # ✅ normalize assistant message safely
        assistant_msg = {
            "role": "assistant",
            "content": msg.content,
        }

        if msg.tool_calls:
            assistant_msg["tool_calls"] = msg.tool_calls

        messages.append(assistant_msg)

        if not msg.tool_calls:
            return (msg.content or "").strip(), trace

        for tc in msg.tool_calls:
            args = _safe_json_loads(tc.function.arguments)

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


def answer_question(client, question: str, *, api_key: str | None = None):

    chart_payload = None
    clean = question.lower().strip()

    if any(g in clean for g in GREETINGS):
        return (
            "Hi 👋 I can help with stocks, prices, and analysis. What do you want to check?",
            [],
            None,
        )

    if clean in {"thanks", "thank you"}:
        return ("You're welcome 🙂", [], None)

    if clean in {"bye", "goodbye"}:
        return ("Goodbye 👋", [], None)

    # ───────── OPENAI MODE ─────────
    if api_key:
        try:
            answer, trace = run_openai_agent(client, api_key, question)
        except Exception as e:
            return (f"Error: {e}", [], None)

    # ───────── FALLBACK MODE ─────────
    else:
        routed = _rule_based_tool_call(question)

        if not routed:
            return ("Try asking about AAPL, MSFT, TSLA 🙂", [], None)

        tool, args = routed
        raw = execute_tool(client, tool, args)

        trace = [{"tool": tool, "input": args, "output": raw}]
        payload = _safe_json_loads(raw)

        if tool == "get_latest_price":
            answer = f"{payload.get('symbol')} ≈ {payload.get('close')}"

        elif tool == "get_asset_price_history":
            s = payload.get("summary", {})
            answer = f"{payload.get('symbol')} moved {s.get('start_close')} → {s.get('end_close')}"

        elif tool == "compare_assets":
            comps = payload.get("comparisons", [])
            answer = " | ".join([f"{c['symbol']} {c['pct_change']}%" for c in comps])

        elif tool == "get_asset_list":
            answer = ", ".join([a["symbol"] for a in payload.get("assets", [])])

        else:
            answer = "Data retrieved."

    # ───────── CHART EXTRACTION ─────────
    for t in trace:
        if t["tool"] != "get_asset_price_history":
            continue

        p = _safe_json_loads(t["output"])
        rows = p.get("data", [])

        if rows:
            chart_payload = {
                "symbol": p.get("symbol"),
                "rows": rows,
            }
            break

    return answer, trace, chart_payload