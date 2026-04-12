"""
services/currency_service.py — Cotações em tempo real + histórico simulado
"""

import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import streamlit as st
import pandas as pd
import requests

from config import EXCHANGE_API_KEY, BASE_CURRENCY, CURRENCIES

log = logging.getLogger(__name__)

_FALLBACK_RATES = {"USD": 5.01, "EUR": 5.42}

# ── Busca cotação atual ───────────────────────────────────────────────────────

def _fetch_from_api(currency: str) -> Optional[float]:
    """Tenta exchangerate-api.com. Requer chave no .env."""
    if not EXCHANGE_API_KEY:
        return None
    try:
        url = (
            f"https://v6.exchangerate-api.com/v6/{EXCHANGE_API_KEY}"
            f"/pair/{currency}/{BASE_CURRENCY}"
        )
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            data = r.json()
            return float(data.get("conversion_rate", 0)) or None
    except Exception as exc:
        log.warning("exchangerate-api falhou: %s", exc)
    return None


def _fetch_from_awesomeapi(currency: str) -> Optional[float]:
    """API gratuita brasileira (sem chave)."""
    try:
        pair = f"{currency}-{BASE_CURRENCY}"
        r = requests.get(
            f"https://economia.awesomeapi.com.br/last/{pair}", timeout=8
        )
        if r.status_code == 200:
            key = pair.replace("-", "")
            return float(r.json()[key]["bid"])
    except Exception as exc:
        log.warning("awesomeapi falhou: %s", exc)
    return None


@st.cache_data(ttl=43200, show_spinner=False)
def get_current_rate(currency: str) -> Dict:
    """Retorna cotação atual com metadados."""
    rate = _fetch_from_awesomeapi(currency) or _fetch_from_api(currency)

    if rate:
        source = "live"
    else:
        # Fallback com pequena variação aleatória para simular mercado
        base = _FALLBACK_RATES.get(currency, 5.0)
        rate = round(base + random.uniform(-0.01, 0.01), 4)
        source = "demo"
        log.warning("Usando cotação demo para %s.", currency)

    return {
        "currency": currency,
        "rate": rate,
        "base": BASE_CURRENCY,
        "source": source,
        "timestamp": datetime.now().isoformat(),
    }


def get_all_rates() -> Dict[str, Dict]:
    return {c: get_current_rate(c) for c in CURRENCIES}


# ── Histórico (últimas 24h simulado / API real se disponível) ────────────────

@st.cache_data(ttl=43200, show_spinner=False)
def get_rate_history(currency: str, hours: int = 24) -> pd.DataFrame:
    """Retorna DataFrame com histórico horário de cotações."""
    history = _fetch_history_awesomeapi(currency, hours)
    if history is None:
        history = _simulate_history(currency, hours)
    return history


def _fetch_history_awesomeapi(currency: str, hours: int) -> Optional[pd.DataFrame]:
    try:
        pair = f"{currency}-{BASE_CURRENCY}"
        r = requests.get(
            f"https://economia.awesomeapi.com.br/json/daily/{pair}/{min(hours, 30)}",
            timeout=10,
        )
        if r.status_code == 200 and r.json():
            rows = [
                {
                    "timestamp": datetime.fromtimestamp(int(d["timestamp"])),
                    "rate": float(d["bid"]),
                }
                for d in r.json()
            ]
            df = pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)
            return df
    except Exception as exc:
        log.warning("Histórico awesomeapi falhou: %s", exc)
    return None


def _simulate_history(currency: str, hours: int) -> pd.DataFrame:
    base = _FALLBACK_RATES.get(currency, 5.01)
    now = datetime.now()
    rows = []
    price = base
    for i in range(hours, -1, -1):
        price += random.uniform(-0.01, 0.01)
        price = max(price, base * 0.9)
        rows.append(
            {"timestamp": now - timedelta(hours=i), "rate": round(price, 4)}
        )
    return pd.DataFrame(rows)


# ── OHLC diário para candlestick ─────────────────────────────────────────────

@st.cache_data(ttl=43200, show_spinner=False)
def get_ohlc(currency: str, days: int = 14) -> pd.DataFrame:
    base = _FALLBACK_RATES.get(currency, 5.01)
    rows, price = [], base
    now = datetime.now().date()
    for i in range(days, -1, -1):
        day_open = price
        high = day_open + random.uniform(0, 0.05)
        low  = day_open - random.uniform(0, 0.05)
        close = random.uniform(low, high)
        rows.append(
            {
                "date": now - timedelta(days=i),
                "open": round(day_open, 4),
                "high": round(high, 4),
                "low":  round(low, 4),
                "close": round(close, 4),
            }
        )
        price = close
    return pd.DataFrame(rows)
