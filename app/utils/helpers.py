"""
utils/helpers.py — Injeção de CSS, PWA e formatação
"""

import os
import streamlit as st
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
        <link rel="manifest" href="/app/static/manifest.json">
        <meta name="theme-color" content="#0d1117">
        <meta name="mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
        <meta name="apple-mobile-web-app-title" content="Monitor Câmbio">
        <script>
          if ('serviceWorker' in navigator) {
            window.addEventListener('load', () => {
              navigator.serviceWorker.register('/app/static/service_worker.js')
                .catch(err => console.warn('SW:', err));
            });
          }
        </script>
        """,
        unsafe_allow_html=True,
    )


def render_nav():
    """Barra de navegação lateral personalizada."""
    page = st.session_state.get("current_page", "dashboard")
    user = st.session_state.get("user_name", "")

    with st.sidebar:
        st.markdown(
            f"""
            <div style='padding:1rem 0 0.5rem;text-align:center;'>
                <div style='font-size:2rem;'>💱</div>
                <div style='font-size:1.1rem;font-weight:700;color:#00d4ff;'>Monitor de Câmbio</div>
                <div style='font-size:0.8rem;color:#8892a4;margin-top:0.2rem;'>Olá, {user} 👋</div>
            </div>
            <hr style='border-color:#21262d;margin:0.5rem 0;'>
            """,
            unsafe_allow_html=True,
        )

        if st.button(
            "📊  Dashboard",
            use_container_width=True,
            type="primary" if page == "dashboard" else "secondary",
        ):
            st.session_state["current_page"] = "dashboard"
            st.rerun()

        if st.button(
            "🤖  Câmbio Auto",
            use_container_width=True,
            type="primary" if page == "cambio_auto" else "secondary",
        ):
            st.session_state["current_page"] = "cambio_auto"
            st.rerun()

        st.markdown("<hr style='border-color:#21262d;'>", unsafe_allow_html=True)

        # Histórico de alertas inline
        alerts = st.session_state.get("alert_history", [])
        if alerts:
            st.markdown("**🔔 Últimos alertas**")
            for a in alerts[:3]:
                icon = "📉" if a["trigger"] == "min" else "📈"
                st.markdown(
                    f"<small style='color:#8892a4;'>{icon} {a['currency']} "
                    f"R${a['rate']:.4f} — {a['time']}</small>",
                    unsafe_allow_html=True,
                )

        st.markdown("<hr style='border-color:#21262d;'>", unsafe_allow_html=True)
        if st.button("🚪 Sair", use_container_width=True):
            from components.auth import logout
            logout()


def fmt_brl(value: float) -> str:
    return f"R$ {value:,.4f}".replace(",", "X").replace(".", ",").replace("X", ".")


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


def _default_css() -> str:
    """CSS embutido de fallback caso assets/styles.css não exista."""
    return ""
