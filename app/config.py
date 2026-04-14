import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega variáveis do .env (na raiz do projeto)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

import streamlit as st

def get_secret(key, default=""):
    """Busca segredo priorizando st.secrets (Cloud) e depois os.getenv (Local)."""
    try:
        if key in st.secrets:
            return st.secrets[key]
    except:
        pass
    return os.getenv(key, default)

# ── Configurações Gerais do App ──────────────────────────────────────────────
APP_CONFIG = {
    "title": "Monitor de Câmbio",
    "icon": "💸",
    "version": "1.3.0",  # Versão melhorada com otimizações
    "refresh_interval": 30,         # segundos entre verificações (30s para real-time)
    "robot_duration_h": 24,        # duração do robô em horas
}

# ── Autenticação (simplificada) ──────────────────────────────────────────────
AUTH_CONFIG = {
    "user": "admin",
    "password": "123",
}

# ── Banco de Usuários (usado pelo view_cambio_auto) ─────────────────────────
USERS = {
    "admin": {
        "name": "Administrador",
        "email": get_secret("ADMIN_EMAIL", "admin@exemplo.com"),
    },
    "usuario": {
        "name": "Usuário Demo",
        "email": get_secret("DEMO_EMAIL", ""),
    },
}

# ── Moedas monitoradas ───────────────────────────────────────────────────────
CURRENCIES = {
    "USD": {"label": "Dólar Americano", "flag": "🇺🇸", "symbol": "US$"},
    "EUR": {"label": "Euro",            "flag": "🇪🇺", "symbol": "€"},
}
BASE_CURRENCY = "BRL"

# ── Navegação ────────────────────────────────────────────────────────────────
PAGES = {
    "dashboard": {"icon": "📊", "label": "Dashboard"},
    "cambio_auto": {"icon": "🤖", "label": "Câmbio Auto"},
    "b3_radar": {"icon": "🔍", "label": "Radar de Ações"},
}

# ── Chaves de API ────────────────────────────────────────────────────────────
EXCHANGE_API_KEY = get_secret("EXCHANGE_API_KEY") or get_secret("EXCHANGE_RATE_API_KEY")
NEWS_API_KEY = get_secret("NEWS_API_KEY")

# ── Telegram ──
TELEGRAM_BOT_TOKEN = get_secret("TELEGRAM_BOT_TOKEN") or get_secret("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = get_secret("TELEGRAM_CHAT_ID")

# ── WhatsApp (CallMeBot) ─────────────────────────────────────────────────────
WHATSAPP_API_KEY = get_secret("WHATSAPP_API_KEY")
WHATSAPP_PHONE = get_secret("WHATSAPP_PHONE")

# ── E-mail SMTP ──────────────────────────────────────────────────────────────
SMTP_HOST = get_secret("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(get_secret("SMTP_PORT", "587"))
SMTP_USER = get_secret("SMTP_USER") or get_secret("EMAIL_USER")
SMTP_PASSWORD = get_secret("SMTP_PASSWORD") or get_secret("EMAIL_PASS")
OPENAI_API_KEY = get_secret("OPENAI_API_KEY")
SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_KEY = get_secret("SUPABASE_KEY")
