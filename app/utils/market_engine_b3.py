"""
Motor de Mercado B3 para o Radar de Ações.
Extrai preços reais via Brapi, HG Brasil e yfinance (fallback).
"""

import pandas as pd
import numpy as np
import random
import threading
import requests
import os
import streamlit as st
from datetime import datetime, timedelta
import yfinance as yf
from collections import deque
import warnings

warnings.filterwarnings('ignore')
import logging
logging.getLogger('yfinance').setLevel(logging.CRITICAL)

# Cores consistentes com o projeto
BLUE      = "#378ADD"
AMBER     = "#EF9F27"
TEAL      = "#1D9E75"
GRAY      = "#888780"
RED       = "#E24B4A"
TEXT      = "#1A1A18"
TEXT2     = "#5F5E5A"
BORDER    = "#D3D1C7"
TEAL_LITE = "#E1F5EE"
TEAL_DARK = "#085041"
AMBER_LT  = "#FAEEDA"
AMBER_DK  = "#633806"
RED_LT    = "#FCEBEB"
RED_DK    = "#791F1F"
GRAY_LT   = "#F1EFE8"
GRAY_DK   = "#444441"
BLUE_LT   = "#E6F1FB"
BLUE_DK   = "#0C447C"

class MarketEngineB3:
    """Motor de mercado ULTRA-RESILIENTE: Brapi (Token) -> HG Brasil -> yfinance."""

    ATIVOS = {
        "ITUB4":     {"nome": "Itaú Unibanco",          "setor": "Banco",      "cor": BLUE,      "fonte": "brapi"},
        "PETR4":     {"nome": "Petrobrás",              "setor": "Energia",    "cor": "#D85A30", "fonte": "brapi"},
        "VALE3":     {"nome": "Vale",                   "setor": "Mineração",  "cor": AMBER,     "fonte": "brapi"},
        "MGLU3":     {"nome": "Magazine Luiza",         "setor": "Retail",     "cor": "#5DCAA5", "fonte": "brapi"},
        "BOVA11":    {"nome": "ETF Ibovespa",           "setor": "ETF",        "cor": TEAL,      "fonte": "brapi"},
        "MXRF11":    {"nome": "FII Diversificado",      "setor": "FII",        "cor": GRAY,      "fonte": "brapi"},
        "WEGE3":     {"nome": "WEG Indústria",          "setor": "Indústria",  "cor": AMBER,     "fonte": "brapi"},
        "BBDC4":     {"nome": "Bradesco",               "setor": "Banco",      "cor": "#7F77DD", "fonte": "brapi"},
    }

    GLOBAL_ATIVOS = {
        "^GSPC":     {"nome": "S&P 500",          "cor": "#FF6B6B"},
        "DXY":       {"nome": "Dólar Index (DXY)","cor": "#4B7BEC"},
    }

    DISPLAY_NAMES = {**{k: v["nome"] for k, v in ATIVOS.items()}, **{k: v["nome"] for k, v in GLOBAL_ATIVOS.items()}}

    EVENTOS = [
        ("Mercado reage positivo - Fluxo de estrangeiros", "positivo"),
        ("Abertura com cautela após dados internacionais", "neutro"),
        ("Banco Central mantém inflação sob controle", "neutro"),
        ("Energia ganha com recuperação do petróleo", "positivo"),
        ("Bancos em queda - Inadimplência acima do previsto", "alerta"),
        ("Varejo se destaca com bom volume", "positivo"),
        ("Inflação abaixo pressiona títulos", "positivo"),
        ("Câmbio recua - exportadores ganham", "positivo"),
        ("Fiscal pressiona no fechamento", "alerta"),
        ("Mineradora beneficiada por commodities", "positivo"),
    ]

    def __init__(self):
        # Tenta carregar o token da Brapi (Secrets ou Env)
        try:
            self.brapi_token = st.secrets.get("BRAPI_TOKEN", os.getenv("BRAPI_TOKEN", ""))
        except:
            self.brapi_token = os.getenv("BRAPI_TOKEN", "")

        self.precos   = {}
        self.abertura = {}
        self.maximos  = {}
        self.minimos  = {}
        self.historico= {k: deque(maxlen=120) for k in {**self.ATIVOS, **self.GLOBAL_ATIVOS}}
        self.variacao = {k: 0.0 for k in {**self.ATIVOS, **self.GLOBAL_ATIVOS}}
        self.last_fetch_source = {k: "brapi" for k in self.ATIVOS}
        self.lock     = threading.Lock()
        self.tick     = 0
        self.last_alert_time = 0
        self._init_precos()

    def _init_precos(self):
        self.tick_mercado()

    def _fetch_hg_indices(self):
        try:
            r = requests.get("https://api.hgbrasil.com/finance/quotations", timeout=3)
            if r.status_code == 200:
                return r.json()["results"]
            return {}
        except: return {}

    def _fetch_fallback_yf(self, ticker):
        """Backup final via yfinance."""
        try:
            yf_ticker = ticker if ticker.endswith(".SA") or "^" in ticker else f"{ticker}.SA"
            data = yf.download(yf_ticker, period="2d", interval="1d", progress=False, threads=False)
            if not data.empty:
                closes = data["Close"].dropna().values.flatten()
                preco = float(closes[-1])
                ref = float(closes[-2]) if len(closes) >= 2 else preco
                return preco, ref, "yahoo"
            return 0, 0, ""
        except: return 0, 0, ""

    def _fetch_data(self, ticker):
        """Lógica Híbrida Individual (Fallback)."""
        # 1. Tenta Brapi Individual
        try:
            params = {}
            if self.brapi_token: params['token'] = self.brapi_token
            url = f"https://brapi.dev/api/quote/{ticker}"
            resp = requests.get(url, params=params, timeout=5)
            data = resp.json()
            if 'results' in data and len(data['results']) > 0:
                res = data['results'][0]
                p = float(res.get('regularMarketPrice', 0))
                r = float(res.get('regularMarketPreviousClose', p))
                if p > 0: return p, r, "brapi"
        except: pass

        # 2. Tenta HG Brasil (Para índices ou moedas)
        if ticker in ["^GSPC", "DXY"]:
            try:
                hg = self._fetch_hg_indices()
                if hg:
                    if ticker == "^GSPC":
                        stk = hg["stocks"]["NASDAQ"]
                        p = float(stk["points"])
                        ref = p / (1 + (float(stk["variation"])/100))
                        return p, ref, "hg_brasil"
                    if ticker == "DXY":
                        currs = hg["currencies"]
                        v_dxy = (currs["EUR"]["variation"] + currs["GBP"]["variation"] + currs.get("JPY", {"variation":0})["variation"]) / 3
                        return 100.0, 100.0 / (1 + (v_dxy/100)), "hg_brasil"
            except: pass

        # 3. yfinance (Último recurso)
        return self._fetch_fallback_yf(ticker)

    def tick_mercado(self):
        from components.notifications import send_telegram
        import time

        with self.lock:
            # --- FASE 1: Busca em Lote (Brapi) ---
            try:
                tickers_str = ",".join(self.ATIVOS.keys())
                params = {}
                if self.brapi_token: params['token'] = self.brapi_token
                url = f"https://brapi.dev/api/quote/{tickers_str}"
                resp = requests.get(url, params=params, timeout=7)
                if resp.status_code == 200:
                    results = resp.json().get('results', [])
                    for res in results:
                        t = res.get('symbol', '').replace('.SA', '')
                        if t in self.ATIVOS:
                            p = float(res.get('regularMarketPrice', 0))
                            if p > 0:
                                self._update_asset_data(t, p, res.get('regularMarketPreviousClose', p), "brapi")
            except: pass

            # --- FASE 2: Fallback para Zeros e Globais ---
            todos = {**self.ATIVOS, **self.GLOBAL_ATIVOS}
            for t in todos.keys():
                # Se o preço ainda for 0 or None, tenta individualmente (Fallback)
                if self.precos.get(t, 0) == 0:
                    p, r, src = self._fetch_data(t)
                    if p > 0:
                        self._update_asset_data(t, p, r, src)

            self.tick += 1

    def _update_asset_data(self, ticker, novo, abertura_ref, fonte):
        import time
        from components.notifications import send_telegram

        if ticker == "^GSPC":
            prev = self.precos.get(ticker)
            if prev and (novo != prev):
                var_inst = (novo / prev - 1) * 100
                if var_inst < -1.5 and (time.time() - self.last_alert_time > 3600):
                    send_telegram(f"⚠️ *ALERTA WALL STREET*: S&P 500 em queda! ({var_inst:.2f}%)")
                    self.last_alert_time = time.time()

        self.precos[ticker] = novo
        self.maximos[ticker] = max(self.maximos.get(ticker, 0), novo)
        self.minimos[ticker] = min(self.minimos.get(ticker, 999999), novo)
        
        if self.abertura.get(ticker, 0) == 0:
            self.abertura[ticker] = abertura_ref if abertura_ref > 0 else novo

        if self.abertura.get(ticker, 0) > 0:
            self.variacao[ticker] = (novo / self.abertura[ticker] - 1) * 100
        
        self.historico[ticker].append(novo)
        if ticker in self.ATIVOS:
            self.ATIVOS[ticker]["fonte"] = fonte

    def sinal(self, ticker):
        hist = list(self.historico[ticker])
        var   = self.variacao.get(ticker, 0)
        preco = self.precos.get(ticker, 0)

        if len(hist) < 20:
            if var <= -5.0: return "ATENÇÃO", RED_LT, RED_DK
            elif var <= -2.0: return "COMPRA", TEAL_LITE, TEAL_DARK
            elif var >= 3.5: return "REALIZAR", AMBER_LT, AMBER_DK
            elif var > 0.5: return "SUBIDA", BLUE_LT, BLUE_DK
            elif var < -0.5: return "RECUO", RED_LT, RED_DK
            else: return "AGUARDAR", GRAY_LT, GRAY_DK

        mm20  = np.mean(hist[-20:])
        mm50  = np.mean(hist[-50:]) if len(hist) >= 50 else mm20
        
        if (var < -1.5 and preco > mm50) or (var < -3.5):
            return "COMPRA", TEAL_LITE, TEAL_DARK
        elif var >= 3.0 or preco > mm20 * 1.05:
            return "REALIZAR", AMBER_LT, AMBER_DK
        elif var <= -7.0:
            return "ATENÇÃO", RED_LT, RED_DK
        elif preco > mm20 * 1.01:
            return "ALTA", BLUE_LT, BLUE_DK
        elif preco < mm20 * 0.99:
            return "RECUO", RED_LT, RED_DK
        return "AGUARDAR", GRAY_LT, GRAY_DK

    def evento_aleatorio(self):
        return random.choice(self.EVENTOS)
