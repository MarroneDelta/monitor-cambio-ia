"""
services/prediction_service.py — Previsão heurística para 48h
"""

import logging
import statistics
from typing import Dict, Optional
import pandas as pd
import streamlit as st

log = logging.getLogger(__name__)


def _trend_slope(values: list) -> float:
    """Calcula inclinação simples por regressão linear leve."""
    n = len(values)
    if n < 2:
        return 0.0
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(values) / n
    num   = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, values))
    denom = sum((x - mean_x) ** 2 for x in xs)
    return num / denom if denom else 0.0


def _volatility(values: list) -> float:
    if len(values) < 2:
        return 0.0
    return statistics.stdev(values)


def predict_48h(
    history_df: pd.DataFrame,
    news_sentiment: float = 0.0,   # -1 (negativo) a +1 (positivo)
) -> Dict:
    """
    Retorna previsão de mínimo e máximo para as próximas 48h.

    Estratégia heurística:
    1. Calcula tendência linear das últimas horas
    2. Aplica volatilidade histórica como banda
    3. Ajusta levemente com sentimento de notícias
    """
    rates = list(history_df["rate"].values)
    if not rates:
        return {"min": 0, "max": 0, "confidence": "baixa"}

    last       = rates[-1]
    slope      = _trend_slope(rates)
    vol        = _volatility(rates) or abs(last * 0.005)
    sentiment_adj = news_sentiment * vol * 0.5   # efeito suave

    # Projeção central após 48 pontos (1 por hora)
    projected = last + slope * 48 + sentiment_adj

    low_band  = projected - vol * 2.0
    high_band = projected + vol * 2.0

    # Garantir que mín < máx
    if low_band >= high_band:
        low_band  = projected * 0.995
        high_band = projected * 1.005

    # Confiança baseada em volume de dados
    if len(rates) >= 20:
        confidence = "alta"
    elif len(rates) >= 10:
        confidence = "média"
    else:
        confidence = "baixa"

    trend_dir = "alta ↑" if slope > 0.0001 else ("queda ↓" if slope < -0.0001 else "estável →")

    return {
        "current":    round(last, 4),
        "min_48h":    round(low_band, 4),
        "max_48h":    round(high_band, 4),
        "projected":  round(projected, 4),
        "trend":      trend_dir,
        "volatility": round(vol, 5),
        "confidence": confidence,
        "sentiment":  news_sentiment,
    }


@st.cache_data(ttl=600, show_spinner=False)
def get_prediction(currency: str, history_df: pd.DataFrame, news_sentiment: float = 0.0) -> Dict:
    return predict_48h(history_df, news_sentiment)
