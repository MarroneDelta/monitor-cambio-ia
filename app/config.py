import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega variáveis do .env (na raiz do projeto)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

# ── Configurações Gerais do App ──────────────────────────────────────────────
APP_CONFIG = {
    "title": "Monitor de Câmbio",
    "icon": "💸",
    "version": "1.2.0",
    "refresh_interval": 3600*12,      # segundos entre verificações (5 min)
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
        "email": os.getenv("ADMIN_EMAIL", "admin@exemplo.com"),
    },
    "usuario": {
        "name": "Usuário Demo",
        "email": os.getenv("DEMO_EMAIL", ""),
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
}

# ── Chaves de API ────────────────────────────────────────────────────────────
EXCHANGE_API_KEY = os.getenv("EXCHANGE_API_KEY") or os.getenv("EXCHANGE_RATE_API_KEY") or ""
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")

# ── Telegram ─────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or ""
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ── WhatsApp (CallMeBot) ─────────────────────────────────────────────────────
WHATSAPP_API_KEY = os.getenv("WHATSAPP_API_KEY", "")
WHATSAPP_PHONE = os.getenv("WHATSAPP_PHONE", "")

# ── E-mail SMTP ──────────────────────────────────────────────────────────────
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER") or os.getenv("EMAIL_USER") or ""
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD") or os.getenv("EMAIL_PASS") or ""
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
