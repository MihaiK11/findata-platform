from __future__ import annotations

import os
import pandas as pd
import streamlit as st

from streamlit_app.components.price_chart import build_price_chart
from streamlit_app.services.assistant_agent import answer_question
from streamlit_app.services.assistant_tools import AssistantToolClient
from streamlit_app.utils.runtime import render_api_sidebar


# ─────────────────────────────────────────────
# CHART RENDERING (FIXED + CLEAN)
# ─────────────────────────────────────────────
def _render_chart(chart_payload: dict) -> None:
    rows = chart_payload.get("rows") or []
    if not rows:
        return

    frame = pd.DataFrame(rows)

    if "date" in frame.columns:
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")

    symbol = chart_payload.get("symbol", "")

    st.plotly_chart(
        build_price_chart(frame, f"{symbol} — price history"),
        use_container_width=True,   # ✅ FIX: correct Streamlit API
        key=f"assistant_chart_{symbol}",
    )


# ─────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────
def render() -> None:
    st.title("Financial Assistant")
    st.caption("Ask naturally — I’ll explain market data in simple terms.")

    api_base = render_api_sidebar()
    client = AssistantToolClient(api_base)

    # API KEY
    api_key = os.getenv("OPENAI_API_KEY", "") or st.sidebar.text_input(
        "OpenAI API key (optional)",
        type="password",
        help="Enables smarter conversational responses.",
    )

    # INIT CHAT HISTORY
    if "assistant_messages" not in st.session_state:
        st.session_state.assistant_messages = [
            {
                "role": "assistant",
                "content": "Hi 👋 Ask me about stocks, trends, or comparisons.",
            }
        ]

    # RENDER HISTORY
    for message in st.session_state.assistant_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            if message.get("chart"):
                _render_chart(message["chart"])

    # USER INPUT
    prompt = st.chat_input("Ask about markets…")
    if not prompt:
        return

    st.session_state.assistant_messages.append(
        {"role": "user", "content": prompt}
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    # ASSISTANT RESPONSE
    with st.chat_message("assistant"):
        with st.spinner("Analyzing market data… 📊"):
            try:
                answer, trace, chart_payload = answer_question(
                    client,
                    prompt,
                    api_key=api_key or None,
                )
            except Exception:
                answer = "I couldn’t fetch the data right now. Try again in a moment."
                trace = []
                chart_payload = None

        st.markdown(answer)

        if chart_payload:
            _render_chart(chart_payload)

        with st.expander("Tool calls (debug)", expanded=False):
            for item in trace:
                st.json(item)

    # SAVE HISTORY
    st.session_state.assistant_messages.append(
        {
            "role": "assistant",
            "content": answer,
            "chart": chart_payload,
        }
    )