"""
services/currency_service.py — Cotações em tempo real + histórico com cache inteligente
Melhorado com fallbacks robustos e APIs mais confiáveis
"""

import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import streamlit as st
import pandas as pd
import requests
import time

from config import EXCHANGE_API_KEY, BASE_CURRENCY, CURRENCIES

log = logging.getLogger(__name__)

_FALLBACK_RATES = {"USD": 5.01, "EUR": 5.42}

# Cache em memória para evitar requisições redundantes
_cache_rates = {}
_cache_timestamp = {}
_cache_ttl = 8  # Segundos entre verificações de cada moeda

# ── Busca cotação atual ───────────────────────────────────────────────────────

def _fetch_from_awesomeapi(currency: str) -> Optional[Dict]:
    """API gratuita brasileira (sem chave) - MELHOR FONTE."""
    try:
        pair = f"{currency}-{BASE_CURRENCY}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"
        }
        r = requests.get(
            f"https://economia.awesomeapi.com.br/last/{pair}", 
            timeout=4, 
            headers=headers
        )
        if r.status_code == 200:
            data = r.json()[pair.replace("-", "")]
            return {
                "rate": float(data["bid"]),
                "change_pct": float(data.get("pctChange", 0.0)),
                "high": float(data.get("high", 0)),
                "low": float(data.get("low", 0)),
                "source": "awesomeapi"
            }
    except Exception as exc:
        log.debug(f"AwesomeAPI falhou para {currency}: {exc}")
    return None


def _fetch_from_hgbrasil(currency: str) -> Optional[Dict]:
    """HG Brasil Finance - BACKUP PRIMÁRIO."""
    try:
        r = requests.get(
            "https://api.hgbrasil.com/finance/quotations", 
            timeout=4
        )
        if r.status_code == 200:
            currs = r.json()["results"]["currencies"]
            if currency in currs:
                data = currs[currency]
                return {
                    "rate": float(data["buy"]),
                    "change_pct": float(data.get("variation", 0)),
                    "high": float(data.get("high", 0)),
                    "low": float(data.get("low", 0)),
                    "source": "hgbrasil"
                }
    except Exception as exc:
        log.debug(f"HG Brasil falhou para {currency}: {exc}")
    return None


def _fetch_from_yfinance(currency: str) -> Optional[Dict]:
    """YFinance como fallback final (mais lento)."""
    try:
        import yfinance as yf
        ticker = f"{currency}{BASE_CURRENCY}=X" if BASE_CURRENCY == "BRL" else f"{currency}{BASE_CURRENCY}"
        
        data = yf.download(ticker, period="1d", interval="1m", progress=False, threads=False)
        if not data.empty:
            closes = data["Close"].dropna()
            if len(closes) >= 2:
                current = float(closes.iloc[-1])
                previous = float(closes.iloc[-2]) if len(closes) >= 2 else current
                change = ((current / previous) - 1) * 100 if previous > 0 else 0
                return {
                    "rate": current,
                    "change_pct": change,
                    "high": float(data["High"].max()),
                    "low": float(data["Low"].min()),
                    "source": "yfinance"
                }
    except Exception as exc:
        log.debug(f"YFinance falhou para {currency}: {exc}")
    return None


def _fetch_from_exchangerate_api(currency: str) -> Optional[Dict]:
    """ExchangeRate-API - FALLBACK (Consumir quota com moderação)."""
    if not EXCHANGE_API_KEY:
        log.debug(f"ExchangeRate-API: Chave não configurada")
        return None
    
    try:
        url = (
            f"https://v6.exchangerate-api.com/v6/{EXCHANGE_API_KEY}"
            f"/pair/{currency}/{BASE_CURRENCY}"
        )
        r = requests.get(url, timeout=4)
        
        if r.status_code == 200:
            data = r.json()
            if "conversion_rate" in data:
                rate = float(data["conversion_rate"])
                log.warning(f"📊 ExchangeRate-API chamada para {currency}: R$ {rate:.4f} (CONSUMINDO QUOTA)")
                return {
                    "rate": rate,
                    "change_pct": 0.0,  # ExchangeRate-API não fornece variação
                    "high": rate * 1.01,
                    "low": rate * 0.99,
                    "source": "exchangerate-api (PAGA)"
                }
        else:
            log.debug(f"ExchangeRate-API Status {r.status_code} para {currency}")
            
    except Exception as exc:
        log.debug(f"ExchangeRate-API falhou para {currency}: {exc}")
    
    return None


@st.cache_data(ttl=60, show_spinner=False)
def _fetch_with_fallbacks(currency: str) -> Dict:
    """Tenta múltiplas APIs em ordem de preferência com fallback automático."""
    
    # 1. Tenta AwesomeAPI (melhor para BRL, GRATUITA)
    result = _fetch_from_awesomeapi(currency)
    if result:
        log.warning(f"✅ AwesomeAPI: {currency}/BRL consultado com sucesso")
        return result
    
    # 2. Tenta HG Brasil (GRATUITA)
    result = _fetch_from_hgbrasil(currency)
    if result:
        log.warning(f"✅ HG Brasil: {currency}/BRL consultado com sucesso")
        return result
    
    # 3. Tenta ExchangeRate-API (PAGA - FALLBACK)
    result = _fetch_from_exchangerate_api(currency)
    if result:
        log.warning(f"⚠️  ExchangeRate-API: {currency}/BRL - QUOTA CONSUMIDA!")
        return result
    
    # 4. Tenta YFinance (GRATUITA mas lenta)
    result = _fetch_from_yfinance(currency)
    if result:
        log.warning(f"⏳ YFinance: {currency}/BRL consultado (LENTO)")
        return result
    
    # 5. Fallback emergencial
    log.warning(f"🔴 TODAS as APIs falharam para {currency}. Usando fallback.")
    return {
        "rate": _FALLBACK_RATES.get(currency, 5.0),
        "change_pct": 0.0,
        "high": _FALLBACK_RATES.get(currency, 5.0) * 1.01,
        "low": _FALLBACK_RATES.get(currency, 5.0) * 0.99,
        "source": "fallback-cache"
    }


def get_current_rate(currency: str) -> Dict:
    """Busca cotação exata com cache inteligente - MAJOR IMPROVEMENT."""
    rate_data = _fetch_with_fallbacks(currency)
    
    return {
        "currency": currency,
        "rate": rate_data["rate"],
        "change_pct": rate_data["change_pct"],
        "high": rate_data.get("high", rate_data["rate"]),
        "low": rate_data.get("low", rate_data["rate"]),
        "base": BASE_CURRENCY,
        "source": rate_data["source"],
        "timestamp": datetime.now().isoformat(),
    }


def get_all_rates() -> Dict[str, Dict]:
    return {c: get_current_rate(c) for c in CURRENCIES}


# ── Histórico (últimas 24h simulado / API real se disponível) ────────────────

@st.cache_data(ttl=600, show_spinner=False)
def get_rate_history(currency: str, hours: int = 24, cache_buster: float = 0.0) -> pd.DataFrame:
    """Retorna histórico real da AwesomeAPI (últimos 30 dias de fechamento)."""
    try:
        pair = f"{currency}-{BASE_CURRENCY}"
        # A AwesomeAPI fornece histórico de fechamentos diários
        r = requests.get(f"https://economia.awesomeapi.com.br/json/daily/{pair}/30", timeout=3)
        if r.status_code == 200:
            data = r.json()
            rows = []
            for item in data:
                # O timestamp da AwesomeAPI é em segundos
                ts = datetime.fromtimestamp(int(item["timestamp"]))
                rows.append({"timestamp": ts, "rate": float(item["bid"])})
            
            df = pd.DataFrame(rows)
            # Ordena do mais antigo para o mais novo para o gráfico
            df = df.sort_values("timestamp")
            
            # Garante que a coluna da tabela seja do tipo Datetime com fuso horário (UTC)
            import pytz
            df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(pytz.UTC)
            
            # Filtra apenas o que for pertinente
            cutoff = pd.Timestamp(datetime.now(pytz.UTC) - timedelta(hours=hours))
            df = df[df["timestamp"] >= cutoff].copy()
            
            if not df.empty:
                return df
    except Exception as e:
        log.warning(f"Erro ao buscar histórico AwesomeAPI: {e}")

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
