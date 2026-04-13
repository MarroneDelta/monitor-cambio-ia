"""
components/notifications.py — Alertas via Telegram, e-mail e in-app
"""

import smtplib
import logging
import streamlit as st
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

    try:
        from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            log.warning(f"[⚠️ TELEGRAM] Erro: Chaves não carregadas. (Token possui {len(TELEGRAM_BOT_TOKEN) if TELEGRAM_BOT_TOKEN else 0} chars)")
            return False
            
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        resp = http_requests.post(
            url,
            json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"},
            timeout=10,
        )
        
        if resp.status_code == 200:
            log.warning("[✅ TELEGRAM] Mensagem enviada com sucesso!")
            return True
        else:
            log.warning(f"[❌ TELEGRAM] Erro no Bot: Status {resp.status_code} - {resp.text}")
            return False
            
    except Exception as exc:
        log.warning(f"[❌ TELEGRAM] Falha na conexão com Telegram: {exc}")
        return False


def send_whatsapp(message: str) -> bool:
    # Verificação de chaves com log explícito para o Cloud
    if not WHATSAPP_API_KEY or not WHATSAPP_PHONE:
        log.warning(f"[⚠️ WHATSAPP] Erro: Chaves ausentes nos Secrets do Streamlit.")
        return False
        
    if http_requests is None:
        log.warning(f"[⚠️ WHATSAPP] Erro: Biblioteca 'requests' não carregou.")
        return False

    try:
        url = "https://api.callmebot.com/whatsapp.php"
        params = {
            "phone": WHATSAPP_PHONE,
            "text": message,
            "apikey": WHATSAPP_API_KEY
        }
        
        log.warning(f"[🤖 WHATSAPP] Enviando para {WHATSAPP_PHONE}...")
        resp = http_requests.get(url, params=params, timeout=15)
        
        # 200 = Enviado instantaneamente | 210 = Colocado na fila (sucesso também)
        if resp.status_code in [200, 210]:
            log.warning(f"[✅ WHATSAPP] Mensagem aceita pelo CallMeBot! (Status {resp.status_code})")
            return True
        else:
            log.warning(f"[❌ WHATSAPP] Erro do CallMeBot: Status {resp.status_code} - {resp.text}")
            return False
            
    except Exception as exc:
        log.warning(f"[❌ WHATSAPP] Falha na conexão: {exc}")
        return False


def send_email(to_address: str, subject: str, body: str) -> bool:
    if not SMTP_USER or not SMTP_PASSWORD or not to_address:
        log.warning("SMTP não configurado.")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_USER
        msg["To"] = to_address
        html = body.replace("\n", "<br>").replace("*", "<b>").replace("_", "<i>")
        msg.attach(MIMEText(body, "plain"))
        msg.attach(MIMEText(f"<html><body>{html}</body></html>", "html"))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_address, msg.as_string())
        return True
    except Exception as exc:
        log.error("Erro SMTP: %s", exc)
        return False


# ── Notificação in-app (session_state) ──────────────────────────────────────

def push_in_app(currency: str, current_rate: float, trigger: str):
    """Adiciona alerta ao histórico em memória para exibição no painel."""
    alerts = st.session_state.setdefault("alert_history", [])
    alerts.insert(
        0,
        {
            "time": datetime.now().strftime("%d/%m %H:%M"),
            "currency": currency,
            "rate": current_rate,
            "trigger": trigger,
        },
    )
    # Mantém apenas os últimos 50 alertas
    st.session_state["alert_history"] = alerts[:50]


# ── Despacho principal ───────────────────────────────────────────────────────

def dispatch_alert(
    currency: str,
    current_rate: float,
    min_target: float,
    max_target: float,
    trigger: str,
    user_email: Optional[str] = None,
    channels: Optional[list] = None,
):
    """Envia alerta por todos os canais selecionados."""
    if channels is None:
        channels = ["In-app (painel)", "WhatsApp", "Telegram"]

    msg = build_alert_message(currency, current_rate, min_target, max_target, trigger)

    # Telegram
    tg_ok = False
    if "Telegram" in channels:
        tg_ok = send_telegram(msg)

    # WhatsApp
    wa_ok = False
    if "WhatsApp" in channels:
        wa_ok = send_whatsapp(msg)

    # E-mail
    email_ok = False
    if "E-mail" in channels and user_email:
        subject = f"🚨 Alerta {currency}/BRL — R$ {current_rate:.4f}"
        email_ok = send_email(user_email, subject, msg)

    # In-app sempre (se selecionado ou padrão)
    # In-app removido da thread para evitar erro de Contexto no Cloud
    # Apenas logs e disparos externos (WA/TG/Email)
    pass

    # Diagnóstico para logs do Streamlit Cloud
    print(f"[🤖 NOTIFICAÇÃO] Canais: {channels}")
    print(f"   ∟ WhatsApp: {'✅ OK' if wa_ok else '❌ FALHOU ou não selecionado'}")
    print(f"   ∟ Telegram: {'✅ OK' if tg_ok else '❌ FALHOU ou não selecionado'}")
    print(f"   ∟ E-mail:   {'✅ OK' if email_ok else '❌ FALHOU ou não selecionado'}")

    return any([wa_ok, tg_ok, email_ok])
