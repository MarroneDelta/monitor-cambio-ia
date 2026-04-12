"""
Monitor de Câmbio — ponto de entrada principal
"""

import streamlit as st
from config import APP_CONFIG, PAGES
from components.auth import check_auth, show_login
from utils.helpers import inject_pwa, inject_css

# ── Configuração da página ──────────────────────────────────────────────────
st.set_page_config(
    page_title=APP_CONFIG["title"],
    page_icon=APP_CONFIG["icon"],
    layout="wide",
    initial_sidebar_state="expanded",
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
    from utils.helpers import render_nav
    from view_cambio_auto import auto_recover_robot
    
    if not st.session_state.get("robot_recovery_checked"):
        auto_recover_robot()
        st.session_state["robot_recovery_checked"] = True
        
    render_nav()
    
    page = st.session_state.get("page", "dashboard")

    if page == "dashboard":
        from view_dashboard import render
        render()
    elif page == "cambio_auto":
        from view_cambio_auto import render
        render()
    elif page == "b3_radar":
        from view_b3_radar import render
        render()


if __name__ == "__main__":
    main()
