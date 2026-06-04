from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import streamlit as st

from streamlit_app.components.asset_selector import render_asset_selector
from streamlit_app.components.price_chart import build_price_chart
from streamlit_app.components.timeseries_table import render_timeseries_table
from streamlit_app.services.api_client import APIClientError
from streamlit_app.utils.formatting import assets_to_browser_frame, normalize_records, page_slice
from streamlit_app.utils.runtime import (
    handle_api_error,
    load_assets,
    load_timeseries,
    refresh_token,
    render_api_sidebar,
)


def _iso_range(start: date | None, end: date | None) -> tuple[str | None, str | None]:
    start_iso = datetime.combine(start, datetime.min.time()).isoformat() if start else None
    end_iso = datetime.combine(end, datetime.max.time()).isoformat() if end else None
    return start_iso, end_iso


def render() -> None:
    st.title("Main Dashboard")

    api_base = render_api_sidebar()
    token = refresh_token()

    st.sidebar.header("Filters")
    try:
        assets = load_assets(api_base, None, None, token)
    except APIClientError as exc:
        handle_api_error(exc)

    symbol = render_asset_selector(assets, key="dashboard_asset")

    st.sidebar.subheader("Date range")
    start_date = st.sidebar.date_input("Start", value=None, key="dashboard_start")
    end_date = st.sidebar.date_input("End", value=None, key="dashboard_end")

    st.sidebar.subheader("Analytics")
    st.sidebar.caption("Open the **Analytics** page for KPIs, moving averages, and forecasts.")

    start_iso, end_iso = _iso_range(start_date, end_date)

    st.subheader("Asset Browser")
    browser = assets_to_browser_frame(assets)
    page_size = 20
    page_count = max((len(browser) - 1) // page_size + 1, 1)
    browser_page = st.number_input("Browser page", min_value=1, max_value=page_count, value=1, step=1)
    st.dataframe(page_slice(browser, int(browser_page), page_size), use_container_width=True, hide_index=True)

    try:
        rows = load_timeseries(api_base, symbol, start_iso, end_iso, 1000, token)
    except APIClientError as exc:
        handle_api_error(exc)

    frame = normalize_records(rows)
    if frame.empty:
        st.warning("No historical prices returned for the selected asset and date range.")
        return

    chart_frame = frame.rename(columns={"date": "timestamp"})
    chart_for_plotly = chart_frame.rename(columns={"timestamp": "date"})

    st.subheader("Price Chart")
    st.plotly_chart(
        build_price_chart(chart_for_plotly, f"{symbol} — Price & Volume"),
        use_container_width=True,
        key=f"price_chart_{symbol}",
    )

    st.subheader("Time Series Table")
    table_cols = [c for c in ["timestamp", "open", "high", "low", "close", "volume"] if c in chart_frame.columns]
    table_frame = chart_frame[table_cols] if table_cols else chart_frame
    render_timeseries_table(table_frame.sort_values("timestamp", ascending=False), key=f"timeseries_{symbol}")
