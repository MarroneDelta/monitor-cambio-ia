#!/usr/bin/env python3
"""
Script para testar ExchangeRate-API e confirmar consumo de quota
"""

import os
import requests
from dotenv import load_dotenv
from pathlib import Path
import json

# Carrega .env
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

EXCHANGE_API_KEY = os.getenv("EXCHANGE_API_KEY") or os.getenv("EXCHANGE_RATE_API_KEY")
BASE_CURRENCY = "BRL"

print("=" * 80)
print("🧪 TESTE DE EXCHANGERATE-API")
print("=" * 80)

if not EXCHANGE_API_KEY:
    print("\n⚠️  CHAVE NÃO ENCONTRADA!")
    print("   Configure EXCHANGE_API_KEY no .env")
    exit(1)

print(f"\n✅ Chave encontrada: {EXCHANGE_API_KEY[:10]}...")

# Teste 1: Verificar conta
print("\n📊 TESTE 1: Verificar Conta/Quota")
print("-" * 80)
try:
    # Endpoint para verificar status da conta
    url = f"https://v6.exchangerate-api.com/v6/{EXCHANGE_API_KEY}/latest/USD"
    resp = requests.get(url, timeout=5)
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Conexão bem-sucedida!")
        print(f"   Base: {data.get('base')}")
        print(f"   Taxa: {data.get('conversion_rates', {}).get('BRL', 'N/A')}")
        print(f"   Status: OK")
    else:
        print(f"❌ Erro {resp.status_code}: {resp.text}")
except Exception as e:
    print(f"❌ Erro de conexão: {e}")

# Teste 2: Fazer requisição de conversão (CONSUMIR QUOTA)
print("\n💰 TESTE 2: Consumir Quota (USD/BRL)")
print("-" * 80)
try:
    url = f"https://v6.exchangerate-api.com/v6/{EXCHANGE_API_KEY}/pair/USD/{BASE_CURRENCY}"
    resp = requests.get(url, timeout=5)
    
    if resp.status_code == 200:
        data = resp.json()
        rate = data.get("conversion_rate", 0)
        print(f"✅ Requisição consumida com sucesso!")
        print(f"   USD/BRL: {rate:.4f}")
        print(f"   ⚠️  QUOTA FOI DECREMENTADA")
        print(f"   Resposta: {json.dumps(data, indent=2)}")
    else:
        print(f"❌ Erro {resp.status_code}")
        if resp.status_code == 429:
            print("   ⚠️  Limite de requisições atingido!")
        elif resp.status_code == 403:
            print("   ⚠️  Chave inválida ou sem permissão")
except Exception as e:
    print(f"❌ Erro: {e}")

# Teste 3: Fazer requisição EUR/BRL
print("\n💰 TESTE 3: Consumir Quota (EUR/BRL)")
print("-" * 80)
try:
    url = f"https://v6.exchangerate-api.com/v6/{EXCHANGE_API_KEY}/pair/EUR/{BASE_CURRENCY}"
    resp = requests.get(url, timeout=5)
    
    if resp.status_code == 200:
        data = resp.json()
        rate = data.get("conversion_rate", 0)
        print(f"✅ Requisição consumida com sucesso!")
        print(f"   EUR/BRL: {rate:.4f}")
        print(f"   ⚠️  QUOTA FOI DECREMENTADA NOVAMENTE")
    else:
        print(f"❌ Erro {resp.status_code}")
except Exception as e:
    print(f"❌ Erro: {e}")

print("\n" + "=" * 80)
print("📋 RESUMO:")
print("=" * 80)
print("""
Se você viu ✅ COM 'Requisição consumida':
  → ExchangeRate-API ESTÁ funcionando
  → QUOTA SERÁ consumida a CADA requisição
  → Verifique em: https://app.exchangerate-api.com/dashboard
  
Cada teste acima consome 1 requisição:
  • Teste 1: +1 req
  • Teste 2: +1 req
  • Teste 3: +1 req
  
Se seu plano é FREE (1,500/mês):
  → 1,500 ÷ 30 dias = ~50 requisições/dia
  → Dashboard atualiza a cada 30s = ~2,880/dia ❌ INSUFICIENTE!
  
Recomendação:
  ✅ Use AwesomeAPI + HG Brasil (GRATUITAS)
  ✅ ExchangeRoute-API apenas como FALLBACK
  ✅ Considere upgrade para plano pago se quiser usar como principal
""")

print("=" * 80)
