"""
pages/cambio_auto.py — Robô de monitoramento automático de câmbio
"""

import streamlit as st
import threading
import time
import logging
from datetime import datetime, timedelta

from utils.helpers import render_nav, fmt_brl
from utils.security import validate_float
from services.currency_service import get_current_rate
from components.notifications import dispatch_alert
from components.charts import gauge_chart
from config import CURRENCIES, APP_CONFIG, USERS

log = logging.getLogger(__name__)

# ── Robô em background ────────────────────────────────────────────────────────

_robot_lock  = threading.Lock()
_robot_state: dict = {}    # estado compartilhado entre threads


def _robot_loop(config: dict):
    """Thread do robô. Executa até expirar ou ser cancelada."""
    currency  = config["currency"]
    min_target = config["min_target"]
    max_target = config["max_target"]
    expires    = config["expires"]
    user_email = config.get("user_email", "")
    interval   = APP_CONFIG["refresh_interval"]

    log.info("Robô iniciado para %s min=%.4f max=%.4f", currency, min_target, max_target)

    while datetime.utcnow() < expires:
        try:
            rate_data = get_current_rate.__wrapped__(currency)   # bypass cache
            rate = rate_data["rate"]

            with _robot_lock:
                _robot_state["last_rate"]  = rate
                _robot_state["last_check"] = datetime.now().strftime("%d/%m %H:%M:%S")
                _robot_state["running"]    = True

            if rate <= min_target:
                log.info("MIN atingido %s: %.4f", currency, rate)
                dispatch_alert(currency, rate, min_target, max_target, "min", user_email)
                with _robot_lock:
                    _robot_state["last_trigger"] = f"MÍN atingido — R$ {rate:.4f}"

            elif rate >= max_target:
                log.info("MAX atingido %s: %.4f", currency, rate)
                dispatch_alert(currency, rate, min_target, max_target, "max", user_email)
                with _robot_lock:
                    _robot_state["last_trigger"] = f"MÁX atingido — R$ {rate:.4f}"

        except Exception as exc:
            log.error("Robô erro: %s", exc)

        time.sleep(interval)

    with _robot_lock:
        _robot_state["running"] = False
        _robot_state["expired"] = True
    log.info("Robô encerrado para %s.", currency)


def _start_robot(config: dict):
    t = threading.Thread(target=_robot_loop, args=(config,), daemon=True)
    t.start()
    with _robot_lock:
        _robot_state.update({
            "running":      True,
            "expired":      False,
            "last_trigger": None,
            "thread":       t,
            "config":       config,
            "last_rate":    None,
            "last_check":   None,
        })


def _stop_robot():
    with _robot_lock:
        _robot_state["expired"] = True
        _robot_state["running"] = False


# ── Render ────────────────────────────────────────────────────────────────────

def render():
    render_nav()

    st.markdown(
        "<h2 style='color:#c9d1d9;margin-bottom:0;'>🤖 Câmbio Auto</h2>"
        "<p style='color:#8892a4;font-size:0.85rem;margin-top:0;'>Robô de monitoramento automático de moedas</p>",
        unsafe_allow_html=True,
    )

    # ── Status atual do robô ─────────────────────────────────────────────────
    with _robot_lock:
        robot_running = _robot_state.get("running", False)
        robot_expired = _robot_state.get("expired", False)
        robot_config  = _robot_state.get("config", {})
        last_rate     = _robot_state.get("last_rate")
        last_check    = _robot_state.get("last_check", "—")
        last_trigger  = _robot_state.get("last_trigger")

    # Badge de status
    if robot_running:
        badge = "<span class='badge badge-green'>● ATIVO</span>"
    elif robot_expired:
        badge = "<span class='badge badge-red'>● EXPIRADO</span>"
    else:
        badge = "<span class='badge badge-gray'>● INATIVO</span>"

    st.markdown(
        f"<div style='margin-bottom:1rem;'>Status do robô: {badge}</div>",
        unsafe_allow_html=True,
    )

    if robot_running and robot_config:
        cfg   = robot_config
        curr  = cfg["currency"]
        exp   = cfg["expires"].strftime("%d/%m %H:%M")
        meta  = CURRENCIES.get(curr, {})

        st.markdown(
            f"""
            <div class="robot-status-card">
                <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:0.5rem;">
                    <div>
                        <div style="font-size:0.75rem;color:#8892a4;">MOEDA</div>
                        <div style="font-size:1.1rem;color:#00d4ff;font-weight:700;">
                            {meta.get('flag','')} {curr}/BRL
                        </div>
                    </div>
                    <div>
                        <div style="font-size:0.75rem;color:#8892a4;">MÍNIMO ALVO</div>
                        <div style="font-size:1.1rem;color:#26de81;font-weight:700;">{fmt_brl(cfg['min_target'])}</div>
                    </div>
                    <div>
                        <div style="font-size:0.75rem;color:#8892a4;">MÁXIMO ALVO</div>
                        <div style="font-size:1.1rem;color:#ff6b6b;font-weight:700;">{fmt_brl(cfg['max_target'])}</div>
                    </div>
                    <div>
                        <div style="font-size:0.75rem;color:#8892a4;">EXPIRA EM</div>
                        <div style="font-size:1rem;color:#f9ca24;font-weight:700;">{exp}</div>
                    </div>
                </div>
                <div style="margin-top:0.8rem;font-size:0.8rem;color:#8892a4;">
                    Última verificação: {last_check} &nbsp;|&nbsp;
                    Cotação atual: {fmt_brl(last_rate) if last_rate else '—'}
                </div>
                {f'<div style="margin-top:0.4rem;font-size:0.85rem;color:#f9ca24;">⚡ {last_trigger}</div>' if last_trigger else ''}
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Gauge
        if last_rate:
            st.plotly_chart(
                gauge_chart(last_rate, cfg["min_target"], cfg["max_target"], f"{curr}/BRL"),
                use_container_width=True,
                config={"displayModeBar": False},
            )

        col_stop, col_renew = st.columns(2)
        with col_stop:
            if st.button("⏹️ Parar robô", use_container_width=True):
                _stop_robot()
                st.success("Robô encerrado.")
                st.rerun()
        with col_renew:
            if st.button("🔄 Renovar 24h", use_container_width=True):
                robot_config["expires"] = datetime.utcnow() + timedelta(
                    hours=APP_CONFIG["robot_duration_h"]
                )
                with _robot_lock:
                    _robot_state["config"] = robot_config
                    _robot_state["expired"] = False
                st.success("Monitoramento renovado por mais 24h!")
                st.rerun()

        st.markdown("---")

    # ── Formulário de configuração ────────────────────────────────────────────
    if not robot_running:
        st.markdown("#### ⚙️ Configurar novo monitoramento")

        with st.form("robot_form", clear_on_submit=False):
            currency = st.selectbox(
                "Moeda a monitorar",
                options=list(CURRENCIES.keys()),
                format_func=lambda c: f"{CURRENCIES[c]['flag']} {c} — {CURRENCIES[c]['label']}",
            )

            # Cotação atual para referência
            rate_now = get_current_rate(currency)["rate"]
            st.markdown(
                f"<small style='color:#8892a4;'>Cotação atual: {fmt_brl(rate_now)}</small>",
                unsafe_allow_html=True,
            )

            col1, col2 = st.columns(2)
            with col1:
                min_input = st.number_input(
                    "📉 Valor mínimo (R$)",
                    min_value=0.01,
                    max_value=9999.0,
                    value=round(rate_now * 0.97, 2),
                    step=0.01,
                    format="%.4f",
                )
            with col2:
                max_input = st.number_input(
                    "📈 Valor máximo (R$)",
                    min_value=0.01,
                    max_value=9999.0,
                    value=round(rate_now * 1.03, 2),
                    step=0.01,
                    format="%.4f",
                )

            notify_channels = st.multiselect(
                "Canais de notificação",
                options=["In-app (painel)", "Telegram", "E-mail"],
                default=["In-app (painel)"],
            )

            submitted = st.form_submit_button("🚀 Iniciar Monitoramento", use_container_width=True, type="primary")

        if submitted:
            if not validate_float(min_input, 0.01, 9999) or not validate_float(max_input, 0.01, 9999):
                st.error("Valores inválidos.")
            elif min_input >= max_input:
                st.error("O valor mínimo deve ser menor que o máximo.")
            else:
                username = st.session_state.get("username", "")
                user_email = USERS.get(username, {}).get("email", "")
                config = {
                    "currency":   currency,
                    "min_target": float(min_input),
                    "max_target": float(max_input),
                    "expires":    datetime.utcnow() + timedelta(hours=APP_CONFIG["robot_duration_h"]),
                    "user_email": user_email,
                    "channels":   notify_channels,
                }
                _start_robot(config)
                st.success(
                    f"✅ Robô iniciado! Monitorando {currency}/BRL por 24h. "
                    f"Verificação a cada {APP_CONFIG['refresh_interval']//60} minutos."
                )
                st.rerun()

    # ── Histórico de alertas ──────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🔔 Histórico de Alertas")

    alerts = st.session_state.get("alert_history", [])
    if not alerts:
        st.markdown(
            "<p style='color:#8892a4;font-size:0.85rem;'>Nenhum alerta disparado ainda.</p>",
            unsafe_allow_html=True,
        )
    else:
        for a in alerts[:20]:
            icon  = "📉" if a["trigger"] == "min" else "📈"
            color = "#26de81" if a["trigger"] == "min" else "#ff6b6b"
            label = "MÍN atingido" if a["trigger"] == "min" else "MÁX atingido"
            st.markdown(
                f"""
                <div class="alert-item">
                    <span style="font-size:1.2rem;">{icon}</span>
                    <div style="flex:1;">
                        <div style="color:{color};font-weight:600;font-size:0.85rem;">{label} — {a['currency']}/BRL</div>
                        <div style="color:#8892a4;font-size:0.75rem;">{a['time']} · Cotação: R$ {a['rate']:.4f}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ── Legenda de funcionamento ─────────────────────────────────────────────
    with st.expander("ℹ️ Como funciona o Câmbio Auto?", expanded=False):
        st.markdown(
            """
            **O robô de monitoramento funciona assim:**

            1. Você define os valores de **mínimo** e **máximo** desejados para a moeda
            2. O sistema inicia uma verificação automática em **background** (fora da tela)
            3. A cada **5 minutos**, o robô busca a cotação atual
            4. Quando a cotação **atingir** o mínimo ou máximo configurado:
               - Uma notificação é gerada no painel
               - Um alerta é enviado via Telegram/e-mail (se configurado no `.env`)
            5. O monitoramento é válido por **24 horas**
            6. Você pode **renovar** ou **cancelar** a qualquer momento

            > ⚠️ O robô utiliza thread em background do Streamlit.
            > Para produção, considere usar Celery + Redis ou Supabase Edge Functions.
            """
        )
