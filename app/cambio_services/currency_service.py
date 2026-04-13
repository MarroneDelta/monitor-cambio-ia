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


@st.cache_data(ttl=10, show_spinner=False)
def get_current_rate(currency: str) -> Dict:
    """Busca cotação exata e calcula variação real para o Dashboard e Robô."""
    rate = None
    change_pct = 0.0
    source = "desconhecido"

    # 1. AwesomeAPI (Melhor fonte para BRL, já traz pctChange)
    try:
        pair = f"{currency}-{BASE_CURRENCY}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get(f"https://economia.awesomeapi.com.br/last/{pair}", timeout=5, headers=headers)
        if r.status_code == 200:
            data = r.json()[pair.replace("-", "")]
            rate = float(data["bid"])
            change_pct = float(data.get("pctChange", 0.0))
            source = "awesomeapi"
    except: pass

    # 2. Yahoo Finance (Restaura cálculo de variação comparando 2 dias)
    if not rate:
        try:
            import yfinance as yf
            ticker = {"USD": "USDBRL=X", "EUR": "EURBRL=X"}.get(currency, f"{currency}BRL=X")
            # Baixa 2 dias para ter o fechamento de ontem e calcular variação
            data = yf.download(ticker, period="2d", interval="1d", progress=False, threads=False)
            if len(data) >= 1:
                closes = data["Close"].dropna().values.flatten()
                rate = float(closes[-1])
                if len(closes) >= 2:
                    change_pct = ((closes[-1] - closes[-2]) / closes[-2]) * 100
                source = "yfinance"
        except: pass

    # 3. HG Brasil Finance 
    if not rate:
        try:
            r = requests.get("https://api.hgbrasil.com/finance/quotations", timeout=5)
            if r.status_code == 200:
                currs = r.json()["results"]["currencies"]
                if currency in currs:
                    rate = float(currs[currency]["buy"])
                    change_pct = float(currs[currency]["variation"])
                    source = "hgbrasil"
        except: pass

    # Fallback Emergencial
    if not rate:
        rate = _FALLBACK_RATES.get(currency, 5.0)
        source = "demo-emergencia"

    return {
        "currency": currency,
        "rate": rate,
        "change_pct": change_pct,
        "base": BASE_CURRENCY,
        "source": source,
        "timestamp": datetime.now().isoformat(),
    }


def get_all_rates() -> Dict[str, Dict]:
    return {c: get_current_rate(c) for c in CURRENCIES}


# ── Histórico (últimas 24h simulado / API real se disponível) ────────────────

@st.cache_data(ttl=600, show_spinner=False)
def get_rate_history(currency: str, hours: int = 24) -> pd.DataFrame:
    """Retorna histórico real (15m) do Yahoo Finance para o gráfico sparkline."""
    try:
        import yfinance as yf
        ticker = {"USD": "USDBRL=X", "EUR": "EURBRL=X"}.get(currency, f"{currency}BRL=X")
        # Puxa 5 dias com intervalo de 15m para um gráfico fluido
        data = yf.download(ticker, period="5d", interval="15m", progress=False, threads=False)
        if not data.empty:
            df = data[["Close"]].copy()
            df.columns = ["rate"]
            df = df.reset_index()
            df.rename(columns={"Datetime": "timestamp", "Date": "timestamp"}, inplace=True)
            # Filtra apenas as últimas N horas
            cutoff = datetime.now() - timedelta(hours=hours)
            df = df[df["timestamp"] >= cutoff].copy()
            if not df.empty:
                return df
    except Exception as e:
        log.warning(f"Erro ao buscar histórico real: {e}")

    # Fallback se a API falhar (não deixa o gráfico em branco)
    return _simulate_history(currency, hours)

def _simulate_history(currency: str, hours: int) -> pd.DataFrame:
    base = _FALLBACK_RATES.get(currency, 5.01)
    now = datetime.now()
    rows = []
    price = base
    for i in range(hours * 4, -1, -1): # Aumentado número de pontos para a linha não ser reta
        price += random.uniform(-0.005, 0.005)
        rows.append({"timestamp": now - timedelta(minutes=i*15), "rate": round(price, 4)})
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
