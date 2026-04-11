"""
Monitor de Câmbio — ponto de entrada principal
"""

import streamlit as st
from config import APP_CONFIG
from components.auth import check_auth, show_login
from utils.helpers import inject_pwa, inject_css

# ── Configuração da página ──────────────────────────────────────────────────
st.set_page_config(
    page_title=APP_CONFIG["title"],
    page_icon=APP_CONFIG["icon"],
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": "Monitor de Câmbio — v1.0",
    },
)

inject_css()
inject_pwa()

# ── Roteamento ──────────────────────────────────────────────────────────────
def main():
    if not check_auth():
        show_login()
        return

    # Importa somente após autenticação
    page = st.session_state.get("current_page", "dashboard")

    if page == "dashboard":
        from pages.dashboard import render
        render()
    elif page == "cambio_auto":
        from pages.cambio_auto import render
        render()


if __name__ == "__main__":
    main()
