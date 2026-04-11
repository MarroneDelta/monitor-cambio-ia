"""
components/charts.py — Gráficos interativos com Plotly
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Optional


DARK_BG    = "#0d1117"
CARD_BG    = "#161b22"
GRID_COLOR = "#21262d"
ACCENT     = "#00d4ff"
ACCENT2    = "#ff6b6b"
TEXT_COLOR = "#c9d1d9"


def _base_layout(title: str = "", height: int = 320) -> dict:
    return dict(
        title=dict(text=title, font=dict(color=TEXT_COLOR, size=14), x=0.02),
        height=height,
        paper_bgcolor=CARD_BG,
        plot_bgcolor=CARD_BG,
        font=dict(color=TEXT_COLOR, family="monospace"),
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis=dict(
            showgrid=True, gridcolor=GRID_COLOR,
            zeroline=False, tickfont=dict(size=10),
        ),
        yaxis=dict(
            showgrid=True, gridcolor=GRID_COLOR,
            zeroline=False, tickfont=dict(size=10),
            tickprefix="R$",
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=11),
            orientation="h",
            y=-0.15,
        ),
        hovermode="x unified",
    )


def line_chart(
    df: pd.DataFrame,
    currency: str,
    color: str = ACCENT,
    height: int = 320,
) -> go.Figure:
    """Gráfico de linha para histórico de cotação."""
    fig = go.Figure()

    # Área preenchida
    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=df["rate"],
            name=currency,
            mode="lines",
            line=dict(color=color, width=2),
            fill="tozeroy",
            fillcolor=color.replace(")", ",0.08)").replace("rgb", "rgba")
            if color.startswith("rgb")
            else color + "15",
            hovertemplate="R$ %{y:.4f}<extra></extra>",
        )
    )

    layout = _base_layout(f"Histórico {currency}/BRL", height)
    fig.update_layout(**layout)
    return fig


def candlestick_chart(df: pd.DataFrame, currency: str, height: int = 340) -> go.Figure:
    """Gráfico de velas (OHLC simulado por período)."""
    fig = go.Figure(
        data=go.Candlestick(
            x=df["date"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            increasing_line_color="#26de81",
            decreasing_line_color=ACCENT2,
        )
    )
    layout = _base_layout(f"Variação Diária {currency}/BRL", height)
    layout["yaxis"]["tickprefix"] = "R$"
    fig.update_layout(**layout)
    return fig


def gauge_chart(value: float, min_val: float, max_val: float, label: str) -> go.Figure:
    """Gauge indicando posição da cotação no intervalo configurado."""
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=value,
            title={"text": label, "font": {"color": TEXT_COLOR, "size": 13}},
            number={"prefix": "R$ ", "font": {"color": ACCENT, "size": 22}},
            gauge={
                "axis": {"range": [min_val * 0.98, max_val * 1.02],
                         "tickcolor": TEXT_COLOR},
                "bar": {"color": ACCENT},
                "bgcolor": CARD_BG,
                "bordercolor": GRID_COLOR,
                "steps": [
                    {"range": [min_val * 0.98, min_val], "color": "#26de8130"},
                    {"range": [min_val, max_val],         "color": "#f9ca2430"},
                    {"range": [max_val, max_val * 1.02],  "color": ACCENT2 + "30"},
                ],
                "threshold": {
                    "line": {"color": ACCENT2, "width": 2},
                    "thickness": 0.8,
                    "value": max_val,
                },
            },
        )
    )
    fig.update_layout(
        height=220,
        paper_bgcolor=CARD_BG,
        font=dict(color=TEXT_COLOR),
        margin=dict(l=20, r=20, t=40, b=10),
    )
    return fig


def mini_sparkline(values: list, color: str = ACCENT) -> go.Figure:
    """Sparkline compacto para cards."""
    fig = go.Figure(
        go.Scatter(
            y=values,
            mode="lines",
            line=dict(color=color, width=1.5),
            fill="tozeroy",
            fillcolor=color + "20",
        )
    )
    fig.update_layout(
        height=60,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig
