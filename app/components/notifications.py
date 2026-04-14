"""
components/notifications.py — Alertas via Telegram, e-mail e in-app (OTIMIZADO)
"""

import smtplib
import logging
import streamlit as st
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional

try:
    import requests as http_requests
except ImportError:
    http_requests = None

from config import (
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
    WHATSAPP_API_KEY, WHATSAPP_PHONE,
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD,
)

log = logging.getLogger(__name__)

# Thread pool para não bloquear
_notification_lock = threading.Lock()


# ── Template de mensagem ─────────────────────────────────────────────────────

def build_alert_message(
    currency: str,
    current_rate: float,
    min_target: float,
    max_target: float,
    trigger: str = "min",
) -> str:
    icon = "📉" if trigger == "min" else "📈"
    return (
        f"🚨 <b>Alerta de Câmbio</b>\n\n"
        f"A moeda <b>{currency}/BRL</b> atingiu o valor definido!\n\n"
        f"💰 Valor atual: <b>R$ {current_rate:.4f}</b>\n"
        f"📉 Mínimo: R$ {min_target:.4f}\n"
        f"📈 Máximo: R$ {max_target:.4f}\n\n"
        f"{icon} Gatilho: <b>{'mínimo' if trigger == 'min' else 'máximo'} atingido</b>\n\n"
        f"⏱ <i>Monitoramento ativo 24h</i>\n"
        f"— Sistema de Monitoramento de Câmbio\n"
        f"{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    )


# ── Canais de envio ──────────────────────────────────────────────────────────

def send_telegram(message: str) -> bool:
    """Envia mensagem para Telegram com tratamento de erro."""
    try:
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            log.debug("[⚠️ TELEGRAM] Chaves não configuradas")
            return False
            
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        resp = http_requests.post(
            url,
            json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"},
            timeout=5,  # Timeout reduzido
        )
        
        if resp.status_code == 200:
            log.debug("[✅ TELEGRAM] Mensagem enviada")
            return True
        else:
            log.debug(f"[❌ TELEGRAM] Status {resp.status_code}")
            return False
            
    except Exception as exc:
        log.debug(f"[❌ TELEGRAM] Erro: {exc}")
        return False


def send_whatsapp(message: str) -> bool:
    """Envia mensagem para WhatsApp com tratamento de erro."""
    try:
        if not WHATSAPP_API_KEY or not WHATSAPP_PHONE:
            log.debug("[⚠️ WHATSAPP] Chaves não configuradas")
            return False
            
        url = "https://api.callmebot.com/whatsapp.php"
        params = {
            "phone": WHATSAPP_PHONE,
            "text": message,
            "apikey": WHATSAPP_API_KEY
        }
        
        resp = http_requests.get(url, params=params, timeout=5)
        
        # 200 = Enviado | 210 = Fila (sucesso também)
        if resp.status_code in [200, 210]:
            log.debug(f"[✅ WHATSAPP] Status {resp.status_code}")
            return True
        else:
            log.debug(f"[❌ WHATSAPP] Status {resp.status_code}")
            return False
            
    except Exception as exc:
        log.debug(f"[❌ WHATSAPP] Erro: {exc}")
        return False


def send_email(to_address: str, subject: str, body: str) -> bool:
    """Envia e-mail com tratamento de erro."""
    try:
        if not SMTP_USER or not SMTP_PASSWORD or not to_address:
            log.debug("[⚠️ EMAIL] Configuração incompleta")
            return False
            
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_USER
        msg["To"] = to_address
        html = body.replace("\n", "<br>")
        msg.attach(MIMEText(body, "plain"))
        msg.attach(MIMEText(f"<html><body>{html}</body></html>", "html"))
        
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=5) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_address, msg.as_string())
        
        log.debug("[✅ EMAIL] Enviado")
        return True
    except Exception as exc:
        log.debug(f"[❌ EMAIL] Erro: {exc}")
        return False


# ── Despacho principal otimizado ────────────────────────────────────────────

def _dispatch_alert_async(
    currency: str,
    current_rate: float,
    min_target: float,
    max_target: float,
    trigger: str,
    user_email: Optional[str] = None,
    channels: Optional[list] = None,
):
    """Func interna para executar em thread separada."""
    if channels is None:
        channels = ["Telegram"]

    msg = build_alert_message(currency, current_rate, min_target, max_target, trigger)

    results = {
        "telegram": send_telegram(msg) if "Telegram" in channels else False,
        "whatsapp": send_whatsapp(msg) if "WhatsApp" in channels else False,
        "email": send_email(user_email, f"🚨 Alerta {currency}/BRL", msg) if ("E-mail" in channels and user_email) else False,
    }
    
    log.warning(f"[📤 ALERTA] {currency}: TG={results['telegram']}, WA={results['whatsapp']}, EMAIL={results['email']}")


def dispatch_alert(
    currency: str,
    current_rate: float,
    min_target: float,
    max_target: float,
    trigger: str,
    user_email: Optional[str] = None,
    channels: Optional[list] = None,
):
    """
    Envia alerta por todos os canais sem bloquear a thread chamadora.
    Executa em background thread.
    """
    # Executa em thread separada para não bloquear robô
    t = threading.Thread(
        target=_dispatch_alert_async,
        args=(currency, current_rate, min_target, max_target, trigger, user_email, channels),
        daemon=True
    )
    t.start()

