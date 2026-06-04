from __future__ import annotations

import pandas as pd
import streamlit as st

from streamlit_app.utils.formatting import page_slice


def render_timeseries_table(
    frame: pd.DataFrame,
    *,
    page_size: int = 25,
    key: str = "timeseries",
) -> None:
    if frame.empty:
        st.info("No time-series rows to display.")
        return

    st.caption("Click column headers to sort. Use the filters below to narrow rows.")

    numeric_cols = [c for c in frame.columns if c != "timestamp"]
    filter_col = st.selectbox("Filter column", ["—"] + list(frame.columns), key=f"{key}_filter_col")
    working = frame.copy()
    if filter_col != "—" and filter_col in working.columns:
        if pd.api.types.is_numeric_dtype(working[filter_col]):
            min_val, max_val = float(working[filter_col].min()), float(working[filter_col].max())
            low, high = st.slider(
                f"{filter_col} range",
                min_value=min_val,
                max_value=max_val,
                value=(min_val, max_val),
                key=f"{key}_filter_range",
            )
            working = working[(working[filter_col] >= low) & (working[filter_col] <= high)]
        else:
            needle = st.text_input(f"Contains ({filter_col})", key=f"{key}_filter_text")
            if needle:
                working = working[working[filter_col].astype(str).str.contains(needle, case=False, na=False)]

    export_bytes = working.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Export to CSV",
        data=export_bytes,
        file_name="timeseries.csv",
        mime="text/csv",
        key=f"{key}_export",
    )

    page_count = max((len(working) - 1) // page_size + 1, 1)
    page = st.number_input("Page", min_value=1, max_value=page_count, value=1, step=1, key=f"{key}_page")
    page_frame = page_slice(working, int(page), page_size)
    st.dataframe(page_frame, use_container_width=True, hide_index=True, key=f"{key}_view")
