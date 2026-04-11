"""
config.py — Configurações centrais da aplicação
Todas as chaves sensíveis são lidas de variáveis de ambiente.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── App ─────────────────────────────────────────────────────────────────────
APP_CONFIG = {
    "title": "Monitor de Câmbio",
    "icon": "💱",
    "version": "1.0.0",
    "refresh_interval": 300,   # segundos entre atualizações do robô
    "robot_duration_h": 24,    # horas de validade do monitoramento
}

# ── APIs externas ────────────────────────────────────────────────────────────
EXCHANGE_API_KEY  = os.getenv("EXCHANGE_API_KEY", "")     # exchangerate-api.com
NEWS_API_KEY      = os.getenv("NEWS_API_KEY", "")          # newsapi.org
TELEGRAM_TOKEN    = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID  = os.getenv("TELEGRAM_CHAT_ID", "")

# WhatsApp (CallMeBot)
WHATSAPP_API_KEY = os.getenv("WHATSAPP_API_KEY", "")
WHATSAPP_PHONE   = os.getenv("WHATSAPP_PHONE", "")

# Email SMTP (alternativa ao Telegram)
SMTP_HOST     = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", 587))
SMTP_USER     = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

# ── Usuários hard-coded (substitua por banco em produção) ────────────────────
# Senhas armazenadas como bcrypt hash — geradas via utils/security.py
USERS = {
    "admin": {
        "name": "Administrador",
        "password_hash": "$2b$12$KIX/O6nFucl1J3QsJRPJDeD3sVFvW.GXzE7VLEyVsHNmVBLy6Cbsq",
        # hash de "admin123" — altere antes de usar em produção!
        "email": os.getenv("ADMIN_EMAIL", "admin@exemplo.com"),
    },
    "usuario": {
        "name": "Usuário Demo",
        "password_hash": "$2b$12$Ej8rA7yCqIvkDhv3N5UkjeQi5dNgF4xWXq.3hy0JLxw4N.X9N1pYu",
        # hash de "demo123"
        "email": os.getenv("DEMO_EMAIL", ""),
    },
}

# ── Moedas monitoradas ───────────────────────────────────────────────────────
CURRENCIES = {
    "USD": {"label": "Dólar Americano", "flag": "🇺🇸", "symbol": "US$"},
    "EUR": {"label": "Euro",            "flag": "🇪🇺", "symbol": "€"},
}
BASE_CURRENCY = "BRL"
