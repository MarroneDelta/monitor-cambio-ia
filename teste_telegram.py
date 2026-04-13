
import os
import requests
from dotenv import load_dotenv

# Tenta carregar do .env se existir localmente
load_dotenv()

# Pega as chaves (mesmo nome usado no app)
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def testar_envio():
    print(f"--- DIAGNÓSTICO TELEGRAM ---")
    if not TOKEN:
        print("❌ ERRO: TELEGRAM_TOKEN não encontrado nas variáveis de ambiente.")
        return
    if not CHAT_ID:
        print("❌ ERRO: TELEGRAM_CHAT_ID não encontrado nas variáveis de ambiente.")
        return
    
    print(f"✅ Chaves encontradas. Tentando enviar para o Chat ID: {CHAT_ID}...")
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": "🤖 **TESTE DE CONEXÃO MONITOR DE CÂMBIO**\n\nSe você está lendo isso, a comunicação entre o robô e o seu Telegram está funcionando 100%! ✅",
        "parse_mode": "Markdown"
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=15)
        if resp.status_code == 200:
            print("🚀 SUCESSO! Verifique seu Telegram.")
        else:
            print(f"❌ FALHA NO BOT: Status {resp.status_code}")
            print(f"Mensagem do Telegram: {resp.text}")
            print("\n💡 Dica: Verifique se o Bot foi iniciado (/start) ou se o Chat ID está correto.")
    except Exception as e:
        print(f"❌ ERRO EXCEPCIONAL: {e}")

if __name__ == "__main__":
    testar_envio()
