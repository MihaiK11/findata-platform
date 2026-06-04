from __future__ import annotations

import os
from typing import Any

import streamlit as st

from streamlit_app.services.api_client import APIClient, APIClientError

API_BASE_DEFAULT = os.getenv("FINDATA_API_URL", "http://127.0.0.1:8000")


def get_api_client(api_base: str) -> APIClient:
    return APIClient(api_base)


@st.cache_data(show_spinner="Loading assets…")
def load_assets(api_base: str, instrument_class: str | None, region: str | None, _token: int) -> list[dict[str, Any]]:
    return get_api_client(api_base).get_assets(instrument_class=instrument_class, region=region)


@st.cache_data(show_spinner="Loading time series…")
def load_timeseries(
    api_base: str,
    symbol: str,
    start_date: str | None,
    end_date: str | None,
    limit: int,
    _token: int,
) -> list[dict[str, Any]]:
    return get_api_client(api_base).get_timeseries(
        symbol,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )


@st.cache_data(show_spinner="Loading analytics…")
def load_analytics(api_base: str, symbol: str, _token: int) -> dict[str, Any]:
    return get_api_client(api_base).get_analytics(symbol)


def refresh_token() -> int:
    if "refresh_token" not in st.session_state:
        st.session_state.refresh_token = 0
    return int(st.session_state.refresh_token)


def bump_refresh() -> None:
    st.cache_data.clear()
    st.session_state.refresh_token = refresh_token() + 1


def render_api_sidebar() -> str:
    st.sidebar.header("Connection")
    api_base = st.sidebar.text_input("FastAPI base URL", value=API_BASE_DEFAULT)
    if st.sidebar.button("Refresh", use_container_width=True):
        bump_refresh()
    return api_base.rstrip("/")


def handle_api_error(exc: APIClientError) -> None:
    st.error(str(exc))
    st.stop()
