
import os
import requests
import logging
from datetime import datetime
from supabase import create_client, Client

# Configurações via Variáveis de Ambiente (GitHub Secrets)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("RobotWorker")

def get_current_rate_awesome(currency: str) -> float:
    """Busca cotação na AwesomeAPI (Grátis/Ilimitada)."""
    try:
        pair = f"{currency}-BRL"
        r = requests.get(f"https://economia.awesomeapi.com.br/last/{pair}", timeout=10)
        if r.status_code == 200:
            key = pair.replace("-", "")
            return float(r.json()[key]["bid"])
    except Exception as e:
        logger.error(f"Erro ao buscar cotação: {e}")
    return None

def send_telegram_alert(message: str):
    """Envia alerta para o Telegram."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram não configurado.")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
        requests.post(url, json=payload, timeout=10)
        logger.info("Alerta enviado ao Telegram.")
    except Exception as e:
        logger.error(f"Erro ao enviar Telegram: {e}")

def run_worker():
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("Supabase não configurado.")
        return

    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # 1. Busca estado do robô
        res = supabase.table("cambio_monitor_state").select("*").eq("id", "main_robot").execute()
        
        if not res.data:
            logger.info("Nenhuma configuração de robô encontrada.")
            return
            
        config = res.data[0]
        
        if not config.get("is_running"):
            logger.info("Robô está desligado no painel.")
            return

        currency = config.get("currency", "USD")
        min_rate = config.get("min_rate")
        max_rate = config.get("max_rate")
        
        logger.info(f"Monitorando {currency}: Alvo Min {min_rate} | Alvo Max {max_rate}")

        # 2. Busca cotação atual
        rate = get_current_rate_awesome(currency)
        if not rate:
            logger.error("Não foi possível obter a cotação.")
            return
            
        logger.info(f"Cotação Atual: R$ {rate}")

        # 3. Verifica limites
        triggered = False
        msg = ""
        
        if min_rate and rate <= min_rate:
            triggered = True
            msg = f"🟢 <b>ALERTA DE COMPRA!</b>\n\n{currency}/BRL atingiu <b>R$ {rate:.4f}</b> (Meta: R$ {min_rate:.4f})"
        elif max_rate and rate >= max_rate:
            triggered = True
            msg = f"🔴 <b>ALERTA DE VENDA!</b>\n\n{currency}/BRL atingiu <b>R$ {rate:.4f}</b> (Meta: R$ {max_rate:.4f})"

        if triggered:
            # Envia alerta
            send_telegram_alert(msg)
            # Atualiza banco para registro
            supabase.table("cambio_monitor_state").update({"updated_at": datetime.now().isoformat()}).eq("id", "main_robot").execute()
        else:
            logger.info("Cotação dentro do intervalo. Nenhum alerta necessário.")

    except Exception as e:
        logger.error(f"Erro geral no worker: {e}")

if __name__ == "__main__":
    run_worker()
