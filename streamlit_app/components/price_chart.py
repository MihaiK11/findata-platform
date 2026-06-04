from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd


def _x_axis(frame: pd.DataFrame) -> pd.Series:
    if "date" in frame.columns:
        return frame["date"]
    if "timestamp" in frame.columns:
        return frame["timestamp"]
    return pd.Series(frame.index)


def build_price_chart(frame: pd.DataFrame, title: str) -> go.Figure:
    if frame.empty:
        return go.Figure().update_layout(title=title, height=560)

    x_axis = _x_axis(frame)
    figure = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        row_heights=[0.72, 0.28],
        subplot_titles=("Close Price", "Volume"),
    )

    if "close" in frame.columns:
        figure.add_trace(
            go.Scatter(
                x=x_axis,
                y=frame["close"],
                mode="lines",
                name="Close",
                line=dict(width=2),
                hovertemplate="Date: %{x}<br>Close: %{y:.2f}<extra></extra>",
            ),
            row=1,
            col=1,
        )

    if "volume" in frame.columns:
        figure.add_trace(
            go.Bar(
                x=x_axis,
                y=frame["volume"],
                name="Volume",
                opacity=0.55,
                marker_color="rgba(99, 110, 250, 0.45)",
                hovertemplate="Date: %{x}<br>Volume: %{y:,.0f}<extra></extra>",
            ),
            row=2,
            col=1,
        )

    figure.update_layout(
        title=title,
        hovermode="x unified",
        template="plotly_white",
        height=560,
        autosize=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        dragmode="zoom",
        margin=dict(l=40, r=20, t=70, b=40),
    )
    figure.update_xaxes(title_text="Date", rangeslider=dict(visible=True), row=2, col=1)
    figure.update_yaxes(title_text="Close", row=1, col=1)
    figure.update_yaxes(title_text="Volume", row=2, col=1)
    return figure


def build_moving_average_chart(frame: pd.DataFrame, title: str) -> go.Figure:
    if frame.empty:
        return go.Figure().update_layout(title=title, height=520)

    x_axis = _x_axis(frame)
    figure = go.Figure()
    palette = {
        "close": "#1f77b4",
        "ma5": "#ff7f0e",
        "ma20": "#2ca02c",
        "ma50": "#d62728",
    }
    labels = {"close": "Close", "ma5": "MA5", "ma20": "MA20", "ma50": "MA50"}

    for column in ("close", "ma5", "ma20", "ma50"):
        if column in frame.columns:
            figure.add_trace(
                go.Scatter(
                    x=x_axis,
                    y=frame[column],
                    mode="lines",
                    name=labels[column],
                    line=dict(width=2 if column == "close" else 1.5, color=palette.get(column)),
                    hovertemplate=f"{labels[column]}: %{{y:.2f}}<extra></extra>",
                )
            )

    figure.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="Price",
        hovermode="x unified",
        template="plotly_white",
        height=520,
        autosize=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        dragmode="zoom",
        xaxis=dict(rangeslider=dict(visible=True)),
        margin=dict(l=40, r=20, t=70, b=40),
    )
    return figure
