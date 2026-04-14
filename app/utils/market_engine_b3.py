"""
Motor de Mercado B3 para o Radar de Ações - OTIMIZADO
Extrai preços reais via Brapi, HG Brasil e yfinance (fallback).
Agora com menos travamentos e melhor cache.
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
import time

warnings.filterwarnings('ignore')
import logging
logging.getLogger('yfinance').setLevel(logging.CRITICAL)

log = logging.getLogger(__name__)

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
    """Motor de mercado OTIMIZADO: Menos travamentos, cache melhor."""

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
        # Tenta carregar o token da Brapi
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
        self.last_update_time = 0
        self._init_precos()

    def _init_precos(self):
        """Inicializa preços com timeout para não travar."""
        self.tick_mercado()

    def _fetch_hg_indices(self):
        """Busca índices globais do HG Brasil com timeout."""
        try:
            r = requests.get(
                "https://api.hgbrasil.com/finance/quotations", 
                timeout=4
            )
            if r.status_code == 200:
                return r.json()["results"]
            return {}
        except Exception as e:
            log.debug(f"HG Brasil falhou: {e}")
            return {}

    def _fetch_fallback_yf(self, ticker, timeout=5):
        """Backup via yfinance - COM TIMEOUT."""
        try:
            yf_ticker = ticker if ticker.endswith(".SA") or "^" in ticker else f"{ticker}.SA"
            # Reduzido para 1 dia para não travar
            data = yf.download(
                yf_ticker, 
                period="1d", 
                interval="1h", 
                progress=False, 
                threads=False,
                timeout=timeout
            )
            if not data.empty:
                closes = data["Close"].dropna().values.flatten()
                if len(closes) > 0:
                    preco = float(closes[-1])
                    ref = float(closes[0]) if len(closes) > 1 else preco
                    return preco, ref, "yfinance"
            return 0, 0, ""
        except Exception as e:
            log.debug(f"YFinance falhou para {ticker}: {e}")
            return 0, 0, ""

    def _fetch_data_individual(self, ticker, timeout=3):
        """Busca dados de UM ticker com fallbacks rápidos."""
        # 1. Tenta Brapi Individual
        try:
            params = {}
            if self.brapi_token: 
                params['token'] = self.brapi_token
            url = f"https://brapi.dev/api/quote/{ticker}"
            resp = requests.get(url, params=params, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                if 'results' in data and len(data['results']) > 0:
                    res = data['results'][0]
                    p = float(res.get('regularMarketPrice', 0))
                    r = float(res.get('regularMarketPreviousClose', p))
                    if p > 0: 
                        return p, r, "brapi"
        except Exception as e:
            log.debug(f"Brapi falhou para {ticker}: {e}")

        # 2. Tenta HG Brasil para índices especiais
        if ticker in ["^GSPC", "DXY"]:
            try:
                hg = self._fetch_hg_indices()
                if hg:
                    if ticker == "^GSPC" and "stocks" in hg:
                        try:
                            stk = hg["stocks"]["NASDAQ"]
                            p = float(stk["points"])
                            ref = p / (1 + (float(stk["variation"])/100)) if stk["variation"] else p
                            return p, ref, "hg_brasil"
                        except:
                            pass
                    if ticker == "DXY" and "currencies" in hg:
                        try:
                            currs = hg["currencies"]
                            eur_var = currs.get("EUR", {}).get("variation", 0)
                            gbp_var = currs.get("GBP", {}).get("variation", 0)
                            jpy_var = currs.get("JPY", {}).get("variation", 0)
                            v_dxy = (eur_var + gbp_var + jpy_var) / 3
                            return 100.0, 100.0 / (1 + (v_dxy/100)) if v_dxy else 100.0, "hg_brasil"
                        except:
                            pass
            except Exception as e:
                log.debug(f"HG Brasil falhou para {ticker}: {e}")

        # 3. YFinance (Último recurso, com timeout curto)
        return self._fetch_fallback_yf(ticker, timeout=2)

    def tick_mercado(self, use_cache=True):
        """Atualiza preços com timeout para não travar a UI."""
        now = time.time()
        
        # Se foi atualizado há menos de 5 segundos, usa cache
        if use_cache and (now - self.last_update_time) < 5:
            return
        
        self.last_update_time = now
        
        # Pequeno escopo de lock para não travar
        try:
            # --- FASE 1: Busca em Lote (Brapi) - COM TIMEOUT ---
            try:
                tickers_str = ",".join(list(self.ATIVOS.keys())[:4])  # Só os 4 primeiros
                params = {"timeout": 3}
                if self.brapi_token: 
                    params['token'] = self.brapi_token
                
                url = f"https://brapi.dev/api/quote/{tickers_str}"
                resp = requests.get(url, params=params, timeout=4)
                
                if resp.status_code == 200:
                    results = resp.json().get('results', [])
                    with self.lock:
                        for res in results:
                            t = res.get('symbol', '').replace('.SA', '')
                            if t in self.ATIVOS:
                                p = float(res.get('regularMarketPrice', 0))
                                if p > 0:
                                    self._update_asset_data(
                                        t, 
                                        p, 
                                        res.get('regularMarketPreviousClose', p), 
                                        "brapi"
                                    )
            except Exception as e:
                log.debug(f"Brapi lote falhou: {e}")

            # --- FASE 2: Fallback para ativos zerados ---
            todos = {**self.ATIVOS, **self.GLOBAL_ATIVOS}
            with self.lock:
                zerados = [t for t in todos.keys() if self.precos.get(t, 0) == 0]
            
            for t in zerados[:3]:  # Max 3 requisições individuais
                try:
                    p, r, src = self._fetch_data_individual(t, timeout=2)
                    if p > 0:
                        with self.lock:
                            self._update_asset_data(t, p, r, src)
                except Exception as e:
                    log.debug(f"Fallback falhou para {t}: {e}")

            self.tick += 1

        except Exception as e:
            log.error(f"Erro geral no tick_mercado: {e}")

    def _update_asset_data(self, ticker, novo, abertura_ref, fonte):
        """Atualiza dados de UM ativo. Deve ser chamado COM LOCK."""
        try:
            if ticker == "^GSPC":
                prev = self.precos.get(ticker)
                if prev and (novo != prev):
                    var_inst = (novo / prev - 1) * 100
                    if var_inst < -1.5 and (time.time() - self.last_alert_time > 3600):
                        try:
                            from components.notifications import send_telegram
                            send_telegram(f"⚠️ *ALERTA WALL STREET*: S&P 500 em queda! ({var_inst:.2f}%)")
                        except:
                            pass
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
        except Exception as e:
            log.error(f"Erro ao atualizar {ticker}: {e}")

    def sinal(self, ticker):
        """Retorna sinal de trading apenas COM LOCK."""
        try:
            with self.lock:
                hist = list(self.historico[ticker])
                var = self.variacao.get(ticker, 0)
                preco = self.precos.get(ticker, 0)

            if len(hist) < 20:
                if var <= -5.0: return "ATENÇÃO", RED_LT, RED_DK
                elif var <= -2.0: return "COMPRA", TEAL_LITE, TEAL_DARK
                elif var >= 3.5: return "REALIZAR", AMBER_LT, AMBER_DK
                elif var > 0.5: return "SUBIDA", BLUE_LT, BLUE_DK
                elif var < -0.5: return "RECUO", RED_LT, RED_DK
                else: return "AGUARDAR", GRAY_LT, GRAY_DK

            mm20 = np.mean(hist[-20:])
            mm50 = np.mean(hist[-50:]) if len(hist) >= 50 else mm20
            
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
        except Exception as e:
            log.error(f"Erro no sinal para {ticker}: {e}")
            return "ERRO", RED_LT, RED_DK

    def evento_aleatorio(self):
        """Retorna evento aleatório."""
        return random.choice(self.EVENTOS)
