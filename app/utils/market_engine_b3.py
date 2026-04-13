"""
Motor de Mercado B3 para o Radar de Ações.
Extrai preços reais via Brapi e yfinance.
"""

import pandas as pd
import numpy as np
import random
import threading
import requests
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
    """Motor de mercado HÍBRIDO: Brapi (real-time) + yfinance (com delay)."""

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
        self.precos   = {}
        self.abertura = {}
        self.maximos  = {}
        self.minimos  = {}
        self.historico= {k: deque(maxlen=120) for k in {**self.ATIVOS, **self.GLOBAL_ATIVOS}}
        self.candles  = {k: deque(maxlen=60)  for k in self.ATIVOS}
        self.volumes  = {k: deque(maxlen=60)  for k in self.ATIVOS}
        self.variacao = {k: 0.0 for k in {**self.ATIVOS, **self.GLOBAL_ATIVOS}}
        self.lock     = threading.Lock()
        self.tick     = 0
        self.last_alert_time = 0 # Para evitar spam de alertas
        self._init_precos()

    def _init_precos(self):
        todos = {**self.ATIVOS, **self.GLOBAL_ATIVOS}
        for ticker in todos.keys():
            try:
                preco, abertura, volume = self._fetch_data(ticker)
                if preco and preco > 0:
                    self.precos[ticker] = preco
                    self.abertura[ticker] = abertura if abertura and abertura > 0 else preco
                    self.maximos[ticker] = preco
                    self.minimos[ticker] = preco
                    self.historico[ticker].append(preco)
                    if self.abertura[ticker] > 0:
                        self.variacao[ticker] = (preco - self.abertura[ticker]) / self.abertura[ticker] * 100
            except:
                pass

    def _fetch_hg_indices(self):
        """Busca índices globais via HG Brasil como redundância."""
        try:
            r = requests.get("https://api.hgbrasil.com/finance/quotations", timeout=3)
            if r.status_code == 200:
                data = r.json()["results"]["stocks"]
                return data
            return {}
        except: return {}

    def _fetch_fallback(self, ticker):
        """Busca via yfinance com proteção de cabeçalhos."""
        try:
            yf_ticker = ticker if ticker.endswith(".SA") or "^" in ticker else f"{ticker}.SA"
            data = yf.download(yf_ticker, period="2d", interval="1d", progress=False, threads=False)
            if not data.empty:
                closes = data["Close"].dropna().values.flatten()
                preco = float(closes[-1])
                ref = float(closes[-2]) if len(closes) >= 2 else preco
                return preco, ref, 0
            return None, 0, 0
        except: return None, 0, 0

    def _fetch_data(self, ticker):
        """Busca cotação tentando Brapi -> Fallback HG/YFinance."""
        # 1. Tenta Brapi (Ativos B3)
        try:
            url = f"https://brapi.dev/api/quote/{ticker}"
            resp = requests.get(url, timeout=5)
            data = resp.json()
            if 'results' in data and len(data['results']) > 0:
                res = data['results'][0]
                p = float(res.get('regularMarketPrice', 0))
                r = float(res.get('regularMarketPreviousClose', p))
                v = float(res.get('regularMarketVolume', 0))
                if p > 0: return p, r, v
        except: pass

        # 2. Tenta HG Brasil (Índices Globais)
        if ticker in ["^GSPC", "DXY"]:
            hg = self._fetch_hg_indices()
            if ticker == "^GSPC" and "NASDAQ" in hg:
                return float(hg["NASDAQ"]["variation"]), 0, 0 

        # 3. Fallback Final (YFinance)
        return self._fetch_fallback(ticker)

    def tick_mercado(self):
        from components.notifications import send_telegram
        import time

        with self.lock:
            todos = {**self.ATIVOS, **self.GLOBAL_ATIVOS}
            for ticker in todos.keys():
                try:
                    novo, abertura_ref, volume = self._fetch_data(ticker)

                    if novo and novo > 0:
                        # Alerta Wall Street
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
                        
                        # Garante que a abertura nunca seja zero se tivermos dados
                        if self.abertura.get(ticker, 0) == 0:
                            self.abertura[ticker] = abertura_ref if abertura_ref > 0 else novo

                        if self.abertura.get(ticker, 0) > 0:
                            self.variacao[ticker] = (novo / self.abertura[ticker] - 1) * 100
                        self.historico[ticker].append(novo)
                except: pass
            self.tick += 1

    def sinal(self, ticker):
        hist = list(self.historico[ticker])
        if len(hist) < 20: return "AGUARDAR", GRAY_LT, GRAY_DK
        preco = hist[-1]
        mm20  = np.mean(hist[-20:])
        mm50  = np.mean(hist[-50:]) if len(hist) >= 50 else mm20
        var   = self.variacao.get(ticker, 0)
        if var < -5 and preco > mm50: return "COMPRA", TEAL_LITE, TEAL_DARK
        elif var > 8: return "REALIZAR", AMBER_LT, AMBER_DK
        elif var < -12: return "ATENÇÃO", RED_LT, RED_DK
        elif preco > mm20 * 1.03: return "AGUARDAR", BLUE_LT, BLUE_DK
        else: return "AGUARDAR", GRAY_LT, GRAY_DK

    def evento_aleatorio(self):
        return random.choice(self.EVENTOS)
