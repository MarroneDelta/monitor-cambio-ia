
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

def get_current_rate(currency: str) -> float:
    """Busca cotação com redundância (AwesomeAPI + HG Brasil) para o Worker."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }
    
    # 1. Tenta AwesomeAPI
    try:
        pair = f"{currency}-BRL"
        r = requests.get(f"https://economia.awesomeapi.com.br/last/{pair}", timeout=10, headers=headers)
        if r.status_code == 200:
            key = pair.replace("-", "")
            return float(r.json()[key]["bid"])
    except Exception as e:
        logger.warning(f"AwesomeAPI falhou no worker: {e}")

    # 2. Tenta HG Brasil (Fallback)
    try:
        r = requests.get("https://api.hgbrasil.com/finance/quotations", timeout=10, headers=headers)
        if r.status_code == 200:
            currs = r.json()["results"]["currencies"]
            if currency in currs:
                return float(currs[currency]["buy"])
    except Exception as e:
        logger.error(f"HG Brasil falhou no worker: {e}")
        
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
        logger.error("❌ Supabase não configurado. Verifique os GitHub Secrets.")
        return

    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # 1. Busca estado do robô
        res = supabase.table("cambio_monitor_state").select("*").eq("id", "main_robot").execute()
        
        if not res.data:
            logger.warning("⚠️ Nenhuma configuração encontrada no Supabase. Configure o robô no painel primeiro.")
            return
            
        config = res.data[0]
        logger.info(f"📋 Configuração carregada: {config}")
        
        if not config.get("is_running"):
            logger.info("⏸️ Robô está desligado no painel. Nenhuma verificação necessária.")
            return

        currency = config.get("currency", "USD")
        min_rate = config.get("min_rate")
        max_rate = config.get("max_rate")

        # Converte para float e trata None/zero
        try:
            min_rate = float(min_rate) if min_rate else None
        except (TypeError, ValueError):
            min_rate = None

        try:
            max_rate = float(max_rate) if max_rate else None
        except (TypeError, ValueError):
            max_rate = None

        logger.info(f"🎯 Monitorando {currency}: Alvo Min={min_rate} | Alvo Max={max_rate}")

        if not min_rate and not max_rate:
            logger.warning("⚠️ Nenhuma meta definida (min_rate e max_rate estão vazios). Configure no painel.")
            return

        # 2. Busca cotação atual
        rate = get_current_rate(currency)
        if not rate:
            logger.error("❌ Não foi possível obter a cotação. APIs podem estar inacessíveis.")
            return
            
        logger.info(f"💱 Cotação Atual: R$ {rate:.4f}")

        # 3. Verifica limites
        triggered = False
        msg = ""
        
        if min_rate and rate <= min_rate:
            triggered = True
            msg = (
                f"🟢 <b>ALERTA DE COMPRA!</b>\n\n"
                f"{currency}/BRL atingiu <b>R$ {rate:.4f}</b>\n"
                f"Meta mínima: R$ {min_rate:.4f}\n"
                f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            )
            logger.info(f"🚨 META MÍNIMA ATINGIDA! R$ {rate:.4f} <= R$ {min_rate:.4f}")
        elif max_rate and rate >= max_rate:
            triggered = True
            msg = (
                f"🔴 <b>ALERTA DE VENDA!</b>\n\n"
                f"{currency}/BRL atingiu <b>R$ {rate:.4f}</b>\n"
                f"Meta máxima: R$ {max_rate:.4f}\n"
                f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            )
            logger.info(f"🚨 META MÁXIMA ATINGIDA! R$ {rate:.4f} >= R$ {max_rate:.4f}")
        else:
            logger.info(f"✅ Cotação dentro do intervalo. Min={min_rate} | Atual={rate:.4f} | Max={max_rate}")

        if triggered:
            send_telegram_alert(msg)
            supabase.table("cambio_monitor_state").update({
                "updated_at": datetime.now().isoformat(),
                "last_alert_rate": rate,
            }).eq("id", "main_robot").execute()

    except Exception as e:
        logger.error(f"❌ Erro geral no worker: {e}", exc_info=True)

if __name__ == "__main__":
    logger.info("🤖 Worker iniciado")
    run_worker()
    logger.info("🏁 Worker finalizado")
