import streamlit as st
import time
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

ASSETS_DIR = Path(__file__).parent.parent / "assets"

def inject_css():
    css_path = ASSETS_DIR / "styles.css"
    if css_path.exists():
        css = css_path.read_text(encoding="utf-8")
    else:
        css = _default_css()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

def inject_pwa():
    """Injeta link para manifest e service worker no <head>."""
    st.markdown(
        """
        <link rel="manifest" href="/manifest.json">
        <link rel="apple-touch-icon" href="/icon.png">
        <meta name="theme-color" content="#0d1117">
        <meta name="mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
        <meta name="apple-mobile-web-app-title" content="Monitor Câmbio">
        <script>
          if ('serviceWorker' in navigator) {
            window.addEventListener('load', () => {
              navigator.serviceWorker.register('/service-worker.js')
                .then(reg => console.log('PWA Service Worker registrado', reg))
                .catch(err => console.log('Falha no PWA Service Worker', err));
            });
          }
        </script>
        """,
        unsafe_allow_html=True
    )

def render_nav():
    """Menu lateral customizado e responsivo."""
    from config import PAGES
    
    with st.sidebar:
        st.markdown(
            f"""
            <div style="text-align:center; padding:1.5rem 0;">
                <div style="font-size:3rem; margin-bottom:0.5rem;">💸</div>
                <h3 style="margin:0; color:#c9d1d9;">Monitor de Câmbio</h3>
                <p style="font-size:0.8rem; color:#8892a4;">Olá, Administrador 👋</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        page = st.session_state.get("page", "dashboard")
        
        for p_id, p_info in PAGES.items():
            if st.button(
                f"{p_info['icon']}  {p_info['label']}",
                key=f"nav_{p_id}",
                use_container_width=True,
                type="primary" if page == p_id else "secondary"
            ):
                st.session_state.page = p_id
                st.rerun()
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("🚪 Sair", use_container_width=True, key="logout"):
            st.toast("Encerrando sessão...")
            time.sleep(0.5)
            st.session_state["authenticated"] = False
            st.session_state["username"] = None
            st.session_state["page"] = "login"
            st.rerun()

def fmt_brl(val: float) -> str:
    return f"R$ {val:.4f}"

def trend_badge(trend: str) -> str:
    if "↑" in trend:
        return f"<span style='color:#26de81;font-weight:700;'>{trend}</span>"
    if "↓" in trend:
        return f"<span style='color:#ff6b6b;font-weight:700;'>{trend}</span>"
    return f"<span style='color:#f9ca24;font-weight:700;'>{trend}</span>"

def confidence_badge(conf: str) -> str:
    colors = {"alta": "#26de81", "média": "#f9ca24", "baixa": "#ff6b6b"}
    c = colors.get(conf, "#8892a4")
    return f"<span style='background:{c}22;color:{c};border:1px solid {c}44;padding:2px 8px;border-radius:12px;font-size:0.75rem;'>{conf}</span>"

def sentiment_badge(score: float) -> str:
    if score > 0.1:
        label, color = "Positivo", "#26de81"
    elif score < -0.1:
        label, color = "Negativo", "#ff6b6b"
    else:
        label, color = "Neutro", "#f9ca24"
    return f"<span style='background:{color}22;color:{color};border:1px solid {color}44;padding:2px 8px;border-radius:12px;font-size:0.75rem;'>{label}</span>"

def _default_css() -> str:
    return """
    /* Fallback styles */
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    """
