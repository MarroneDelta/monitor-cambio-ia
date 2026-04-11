"""
utils/security.py — Funções de segurança
"""

import re
import html
import bcrypt
import logging

log = logging.getLogger(__name__)

_ALLOWED_INPUT = re.compile(r"[^\w\s@.\-_]")   # só caracteres seguros


def sanitize_input(value: str, max_len: int = 256) -> str:
    """
    Remove caracteres perigosos e escapa HTML.
    Previne XSS e injection básico.
    """
    if not isinstance(value, str):
        return ""
    cleaned = html.escape(value.strip())
    cleaned = _ALLOWED_INPUT.sub("", cleaned)
    return cleaned[:max_len]


def hash_password(plain: str) -> str:
    """Gera hash bcrypt. Use via CLI: python -c 'from utils.security import hash_password; print(hash_password(\"sua_senha\"))'"""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()


def validate_float(value, min_val: float = 0.0, max_val: float = 1_000_000.0) -> bool:
    try:
        f = float(value)
        return min_val <= f <= max_val
    except (TypeError, ValueError):
        return False


def mask_api_key(key: str) -> str:
    """Mascara chave para exibição em logs."""
    if not key or len(key) < 8:
        return "****"
    return key[:4] + "****" + key[-4:]
