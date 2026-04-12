
import requests
import json

def test_apis():
    print("--- 🔍 TESTE DE APIs DE CÂMBIO ---")
    
    # Teste AwesomeAPI
    try:
        print("\n1. Testando AwesomeAPI (Gratuita)...")
        r = requests.get("https://economia.awesomeapi.com.br/last/USD-BRL", timeout=10)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            bid = r.json()["USDBRL"]["bid"]
            print(f"✅ SUCESSO! Valor recebido: R$ {bid}")
        else:
            print(f"❌ FALHOU! Erro: {r.text}")
    except Exception as e:
        print(f"❌ ERRO DE CONEXÃO: {e}")

    # Teste ExchangeRate-API
    # (Pular se não houver chave, mas vamos testar a conectividade básica)
    try:
        print("\n2. Testando conectividade com ExchangeRate-API...")
        r = requests.get("https://v6.exchangerate-api.com/v6/test/pair/USD/BRL", timeout=10)
        print(f"Status: {r.status_code} (Esperado 403/401 se sem chave, mas mostra que há rede)")
    except Exception as e:
        print(f"❌ ERRO DE CONEXÃO: {e}")

if __name__ == "__main__":
    test_apis()
