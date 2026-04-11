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


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    """Converte hexadecimal para rgba compatível com Plotly."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {alpha})"


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
    color: str = "#00d4ff",
    height: int = 320,
) -> go.Figure:
    """Gráfico de linha para histórico de cotação."""
    fig = go.Figure()

    # Área preenchida
    fill_color = _hex_to_rgba(color, 0.1) if color.startswith("#") else color.replace("rgb", "rgba").replace(")", ",0.1)")

    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=df["rate"],
            name=currency,
            mode="lines+markers",
            line=dict(color=color, width=2),
            marker=dict(size=6, symbol="circle", opacity=0.8),
            fill="tozeroy",
            fillcolor=fill_color,
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
            decreasing_line_color="#ff6b6b",
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
                    {"range": [min_val * 0.98, min_val], "color": "rgba(38, 222, 129, 0.15)"},
                    {"range": [min_val, max_val],         "color": "rgba(249, 202, 36, 0.15)"},
                    {"range": [max_val, max_val * 1.02],  "color": "rgba(255, 107, 107, 0.15)"},
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


def mini_sparkline(values: list, color: str = "#00d4ff") -> go.Figure:
    """Sparkline compacto para cards."""
    fill_color = _hex_to_rgba(color, 0.2) if color.startswith("#") else color.replace("rgb", "rgba").replace(")", ",0.2)")
    
    fig = go.Figure(
        go.Scatter(
            y=values,
            mode="lines",
            line=dict(color=color, width=1.5),
            fill="tozeroy",
            fillcolor=fill_color,
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
