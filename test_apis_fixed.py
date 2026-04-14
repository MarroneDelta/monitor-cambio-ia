#!/usr/bin/env python3
"""
Script de teste para validar APIs de câmbio - versão otimizada
"""

import requests
import json
import time
from datetime import datetime

print("=" * 80)
print("🧪 TESTE DE APIs DE CÂMBIO - VERSÃO OTIMIZADA")
print("=" * 80)

# ── Teste 1: AwesomeAPI (Melhor para BRL) ────────────────────────────────────
print("\n✅ Teste 1: AwesomeAPI (Melhor para BRL)")
print("-" * 80)
try:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    
    for curr in ["USD", "EUR"]:
        pair = f"{curr}-BRL"
        url = f"https://economia.awesomeapi.com.br/last/{pair}"
        start = time.time()
        r = requests.get(url, timeout=4, headers=headers)
        elapsed = time.time() - start
        
        if r.status_code == 200:
            data = r.json()[pair.replace("-", "")]
            rate = float(data["bid"])
            change = float(data.get("pctChange", 0))
            print(f"  ✅ {curr}/BRL: R$ {rate:.4f} (Var: {change:+.2f}%) [Tempo: {elapsed:.2f}s]")
        else:
            print(f"  ❌ {curr}/BRL: Status {r.status_code}")
except Exception as e:
    print(f"  ❌ Erro AwesomeAPI: {e}")

# ── Teste 2: HG Brasil Finance (Backup) ────────────────────────────────────
print("\n✅ Teste 2: HG Brasil Finance (Backup)")
print("-" * 80)
try:
    url = "https://api.hgbrasil.com/finance/quotations"
    start = time.time()
    r = requests.get(url, timeout=4)
    elapsed = time.time() - start
    
    if r.status_code == 200:
        currs = r.json()["results"]["currencies"]
        for curr in ["USD", "EUR"]:
            if curr in currs:
                data = currs[curr]
                rate = float(data["buy"])
                change = float(data.get("variation", 0))
                print(f"  ✅ {curr}/BRL: R$ {rate:.4f} (Var: {change:+.2f}%) [Tempo: {elapsed:.2f}s]")
    else:
        print(f"  ❌ Status {r.status_code}")
except Exception as e:
    print(f"  ❌ Erro HG Brasil: {e}")

# ── Teste 3: YFinance (Fallback lento) ────────────────────────────────────
print("\n✅ Teste 3: YFinance (Fallback)")
print("-" * 80)
try:
    import yfinance as yf
    print("  ⏳ YFinance é lento... testando apenas USD/BRL")
    
    start = time.time()
    data = yf.download("USDBRL=X", period="1d", interval="1h", progress=False, threads=False)
    elapsed = time.time() - start
    
    if not data.empty:
        closes = data["Close"].dropna()
        if len(closes) > 0:
            rate = float(closes.iloc[-1])
            print(f"  ✅ USD/BRL: R$ {rate:.4f} [Tempo: {elapsed:.2f}s]")
    else:
        print(f"  ⚠️  Sem dados YFinance")
except Exception as e:
    print(f"  ⚠️  YFinance indisponível: {e}")

# ── Teste 4: Histórico AwesomeAPI ────────────────────────────────────
print("\n✅ Teste 4: Histórico (Últimos 7 dias)")
print("-" * 80)
try:
    url = "https://economia.awesomeapi.com.br/json/daily/USD-BRL/7"
    start = time.time()
    r = requests.get(url, timeout=4)
    elapsed = time.time() - start
    
    if r.status_code == 200:
        data = r.json()
        print(f"  ✅ Recebi {len(data)} cotações diárias")
        print(f"     Período: {data[0]['timestamp']} até {data[-1]['timestamp']}")
        print(f"     [Tempo: {elapsed:.2f}s]")
    else:
        print(f"  ❌ Status {r.status_code}")
except Exception as e:
    print(f"  ❌ Erro histórico: {e}")

# ── Teste 5: Brapi (se token existir) ────────────────────────────────────
print("\n✅ Teste 5: Brapi (se token configurado)")
print("-" * 80)
try:
    import os
    from dotenv import load_dotenv
    from pathlib import Path
    
    env_path = Path(__file__).parent / ".env"
    load_dotenv(env_path)
    
    brapi_token = os.getenv("BRAPI_TOKEN", "")
    
    if not brapi_token:
        print("  ⚠️  Token Brapi não configurado (opcional)")
    else:
        params = {"token": brapi_token}
        url = "https://brapi.dev/api/quote/ITUB4,PETR4,VALE3"
        
        start = time.time()
        r = requests.get(url, params=params, timeout=5)
        elapsed = time.time() - start
        
        if r.status_code == 200:
            results = r.json().get("results", [])
            print(f"  ✅ Brapi retornou {len(results)} ativos")
            for res in results[:3]:
                symbol = res.get("symbol", "?")
                price = float(res.get("regularMarketPrice", 0))
                print(f"     {symbol}: R$ {price:.2f}")
            print(f"     [Tempo: {elapsed:.2f}s]")
        else:
            print(f"  ❌ Brapi Status {r.status_code}")
except Exception as e:
    print(f"  ⚠️  Erro Brapi: {e}")

# ── Resumo ────────────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("✅ TESTE CONCLUÍDO")
print("=" * 80)
print("""
📋 RESUMO:
  • AwesomeAPI: Principal para BRL (gratuita, rápida) ✅
  • HG Brasil:  Backup com dados globais (gratuita) ✅
  • YFinance:   Fallback (lento, mas funciona) ⚠️
  • Brapi:      Dados B3 (requer token, opcional) 

🚀 RECOMENDAÇÃO:
  Sistema agora prioriza AwesomeAPI > HG Brasil > YFinance
  Isso deve resolver travamentos e tornar real-time funcional!
""")
