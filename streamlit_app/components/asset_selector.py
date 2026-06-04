from __future__ import annotations

from typing import Any

import streamlit as st


def render_asset_selector(
    assets: list[dict[str, Any]],
    *,
    label: str = "Asset",
    key: str = "asset_selector",
    default_symbol: str | None = None,
) -> str:
    symbols = [asset.get("symbol") for asset in assets if asset.get("symbol")]
    if not symbols:
        st.warning("No assets available from the API.")
        st.stop()

    index = 0
    if default_symbol and default_symbol in symbols:
        index = symbols.index(default_symbol)

    return st.sidebar.selectbox(label, symbols, index=index, key=key)
