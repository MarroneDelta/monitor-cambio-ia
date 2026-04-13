"""
Motor de Mercado B3 para o Radar de Ações.
Extrai preços reais via Brapi e yfinance.
"""

import pandas as pd
import numpy as np
import random
import threading
import requests
import yfinance as yf
from datetime import datetime, timedelta
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
        "BOVA11.SA": {"nome": "ETF Ibovespa",           "setor": "ETF",        "cor": TEAL,      "fonte": "yfinance"},
        "MXRF11.SA": {"nome": "FII Diversificado",      "setor": "FII",        "cor": GRAY,      "fonte": "yfinance"},
        "WEGE3.SA":  {"nome": "WEG Indústria",          "setor": "Indústria",  "cor": AMBER,     "fonte": "yfinance"},
        "BBDC4.SA":  {"nome": "Bradesco",               "setor": "Banco",      "cor": "#7F77DD", "fonte": "yfinance"},
    }

    GLOBAL_ATIVOS = {
        "^GSPC":     {"nome": "S&P 500",          "cor": "#FF6B6B"},
        "DX-Y.NYB":  {"nome": "Dólar Index (DXY)","cor": "#4B7BEC"},
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
                preco, abertura, volume = self._fetch_yfinance_com_historico(ticker)
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

    def _fetch_brapi(self, ticker):
        """Busca cotação via Brapi. Retorna (preco_atual, preco_abertura, volume)."""
        try:
            url = f"https://brapi.dev/api/quote/{ticker}"
            resp = requests.get(url, timeout=5)
            data = resp.json()
            if 'results' in data and len(data['results']) > 0:
                result = data['results'][0]
                preco = float(result.get('regularMarketPrice', 0))
                abertura = float(result.get('regularMarketOpen', preco))
                volume = float(result.get('regularMarketVolume', 0))
                return preco, abertura, volume
            return None, 0, 0
        except:
            return None, 0, 0

    def _fetch_yfinance_com_historico(self, ticker):
        """Busca 5 dias de histórico. Retorna (preco_atual, preco_anterior, volume)."""
        try:
            dados = yf.download(ticker, period="5d", interval="1d", progress=False, threads=False)
            if dados.empty:
                return None, 0, 0

            col_data = dados['Close']
            if isinstance(col_data, pd.DataFrame):
                prices = col_data.iloc[:, 0].dropna().values
            else:
                prices = col_data.dropna().values

            valid_prices = [float(p) for p in prices if p > 0]
            if not valid_prices:
                return None, 0, 0

            preco_atual = valid_prices[-1]
            preco_anterior = valid_prices[-2] if len(valid_prices) >= 2 else preco_atual

            # Preenche histórico com os últimos dias para gráfico não ficar plano
            for p in valid_prices:
                self.historico[ticker].append(p)

            return preco_atual, preco_anterior, 0
        except:
            return None, 0, 0

    def _fetch_yfinance(self, ticker):
        """Alias simplificado para tick_mercado. Retorna (preco, abertura_ref, volume)."""
        return self._fetch_yfinance_com_historico(ticker)

    def tick_mercado(self):
        from components.notifications import send_telegram
        import time

        with self.lock:
            todos = {**self.ATIVOS, **self.GLOBAL_ATIVOS}
            for ticker in todos.keys():
                try:
                    fonte = self.ATIVOS.get(ticker, {}).get("fonte", "yfinance")
                    if fonte == "brapi" and ticker in self.ATIVOS:
                        novo, abertura_ref, volume = self._fetch_brapi(ticker)
                    else:
                        novo, abertura_ref, volume = self._fetch_yfinance(ticker)

                    if novo and novo > 0:
                        # Alerta de Volatilidade NYSE (S&P 500)
                        if ticker == "^GSPC":
                            prev = self.precos.get(ticker)
                            if prev:
                                var_instantanea = (novo / prev - 1) * 100
                                if var_instantanea < -1.5 and (time.time() - self.last_alert_time > 3600):
                                    msg = f"⚠️ *ALERTA WALL STREET*: Queda brusca no S&P 500! ({var_instantanea:.2f}%)\nO mercado global está em estresse, dólar pode subir."
                                    send_telegram(msg)
                                    self.last_alert_time = time.time()

                        self.precos[ticker] = novo
                        self.maximos[ticker] = max(self.maximos.get(ticker, 0), novo)
                        self.minimos[ticker] = min(self.minimos.get(ticker, 999999), novo)
                        if self.abertura.get(ticker, 0) > 0:
                            self.variacao[ticker] = (novo / self.abertura[ticker] - 1) * 100
                        self.historico[ticker].append(novo)
                except:
                    pass
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
