from __future__ import annotations

import pandas as pd
import streamlit as st

from streamlit_app.components.asset_selector import render_asset_selector
from streamlit_app.components.price_chart import build_moving_average_chart
from streamlit_app.services.analytics import add_moving_averages
from streamlit_app.services.api_client import APIClientError
from streamlit_app.utils.formatting import format_currency, format_percent, normalize_records, trend_badge
from streamlit_app.utils.runtime import (
    handle_api_error,
    load_analytics,
    load_assets,
    load_timeseries,
    refresh_token,
    render_api_sidebar,
)


def render() -> None:
    st.title("Analytics")

    api_base = render_api_sidebar()
    token = refresh_token()

    try:
        assets = load_assets(api_base, None, None, token)
    except APIClientError as exc:
        handle_api_error(exc)

    symbol = render_asset_selector(assets, label="Symbol", key="analytics_asset")

    try:
        analytics = load_analytics(api_base, symbol, token)
        rows = load_timeseries(api_base, symbol, None, None, 1000, token)
    except APIClientError as exc:
        handle_api_error(exc)

    frame = normalize_records(rows)
    if frame.empty:
        st.warning("No time-series data available for this symbol.")
        st.stop()

    enriched = add_moving_averages(frame)
    mas = analytics.get("moving_averages") or {}

    st.subheader("KPI Cards")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Latest Price", format_currency(analytics.get("latest_price")))
    c2.metric("Forecast Price", format_currency(analytics.get("forecast_next_close")))
    c3.metric("Trend", trend_badge(analytics.get("trend", "Sideways")))
    c4.metric("Volatility", format_percent(analytics.get("volatility")))

    st.subheader("Moving Average Chart")
    st.plotly_chart(
        build_moving_average_chart(enriched, f"{symbol} — Close & Moving Averages"),
        use_container_width=True,
        key=f"ma_chart_{symbol}",
    )

    st.subheader("Statistics Panel")
    stats = pd.DataFrame(
        [
            ["Min", format_currency(analytics.get("min_price"))],
            ["Max", format_currency(analytics.get("max_price"))],
            ["Mean", format_currency(analytics.get("mean_price"))],
            ["Median", format_currency(analytics.get("median_price"))],
            ["Std Dev", format_currency(analytics.get("std_dev"))],
            ["Average daily return", format_percent(analytics.get("average_return"))],
        ],
        columns=["Metric", "Value"],
    )
    st.dataframe(stats, use_container_width=True, hide_index=True)

    st.subheader("Moving averages (latest)")
    ma_row = pd.DataFrame(
        [
            ["MA5", format_currency(mas.get("ma5"))],
            ["MA20", format_currency(mas.get("ma20"))],
            ["MA50", format_currency(mas.get("ma50"))],
        ],
        columns=["Window", "Value"],
    )
    st.dataframe(ma_row, use_container_width=True, hide_index=True)

    st.subheader("Forecast Panel")
    forecast = analytics.get("forecast_next_close")
    st.success(f"Predicted next-day close: {format_currency(forecast)}")
    st.write(
        "Forecast method: **linear regression** over the historical close series "
        "(numpy `polyfit`, degree 1). Trend is derived from the latest **MA5 / MA20 / MA50** crossover."
    )
