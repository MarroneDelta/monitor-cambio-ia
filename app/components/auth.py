"""
components/auth.py — Login, logout e proteção de sessão
"""

import streamlit as st
import bcrypt
from datetime import datetime, timedelta
from config import USERS
from utils.security import sanitize_input


SESSION_LIFETIME_H = 8   # horas de sessão válida


# ── Helpers internos ─────────────────────────────────────────────────────────

def _verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def _set_session(username: str):
    user = USERS[username]
    st.session_state["authenticated"] = True
    st.session_state["username"] = username
    st.session_state["user_name"] = user["name"]
    st.session_state["login_time"] = datetime.utcnow().isoformat()
    st.session_state["current_page"] = "dashboard"


def _session_expired() -> bool:
    login_time = st.session_state.get("login_time")
    if not login_time:
        return True
    elapsed = datetime.utcnow() - datetime.fromisoformat(login_time)
    return elapsed > timedelta(hours=SESSION_LIFETIME_H)


# ── API pública ──────────────────────────────────────────────────────────────

def check_auth() -> bool:
    """Retorna True se o usuário está autenticado e a sessão é válida."""
    if not st.session_state.get("authenticated"):
        return False
    if _session_expired():
        logout()
        return False
    return True


def logout():
    for key in ["authenticated", "username", "user_name", "login_time",
                "current_page", "robot_config"]:
        st.session_state.pop(key, None)
    st.rerun()


def show_login():
    st.markdown(
        """
        <div style='display:flex;justify-content:center;align-items:center;
                    min-height:80vh;flex-direction:column;gap:0.5rem;'>
            <h1 style='color:#00d4ff;font-size:2.5rem;margin:0;'>💱 Monitor de Câmbio</h1>
            <p style='color:#8892a4;font-size:1rem;margin:0 0 2rem;'>
                Monitoramento inteligente de câmbio
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        with st.container():
            st.markdown(
                "<div class='login-card'>",
                unsafe_allow_html=True,
            )
            st.markdown("#### 🔐 Entrar na plataforma")

            username_raw = st.text_input(
                "Usuário",
                placeholder="Digite seu usuário",
                key="login_user",
                label_visibility="collapsed",
            )
            password_raw = st.text_input(
                "Senha",
                type="password",
                placeholder="Digite sua senha",
                key="login_pass",
                label_visibility="collapsed",
            )

            col_btn, col_hint = st.columns([1, 1])
            with col_btn:
                login_clicked = st.button(
                    "Entrar →", use_container_width=True, type="primary"
                )
            with col_hint:
                st.markdown(
                    "<small style='color:#8892a4;'>Demo: admin / admin123</small>",
                    unsafe_allow_html=True,
                )

            if login_clicked:
                username = sanitize_input(username_raw)
                password = sanitize_input(password_raw)

                if not username or not password:
                    st.error("Preencha usuário e senha.")
                elif username not in USERS:
                    st.error("Usuário ou senha inválidos.")
                elif not _verify_password(password, USERS[username]["password_hash"]):
                    st.error("Usuário ou senha inválidos.")
                else:
                    _set_session(username)
                    st.success(f"Bem-vindo, {USERS[username]['name']}!")
                    st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)
