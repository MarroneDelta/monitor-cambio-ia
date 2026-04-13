"""
pages/cambio_auto.py — Robô de monitoramento automático de câmbio
"""

import streamlit as st
import threading
import time
import logging
import uuid
from datetime import datetime, timedelta

log = logging.getLogger(__name__)

from utils.helpers import render_nav, fmt_brl
from utils.security import validate_float
from cambio_services.currency_service import get_current_rate
from components.notifications import dispatch_alert
from components.charts import gauge_chart
from config import CURRENCIES, APP_CONFIG, USERS
from components.auth import get_supabase

log = logging.getLogger(__name__)

# ── Robô em background ────────────────────────────────────────────────────────

_robot_lock  = threading.Lock()
_robot_state: dict = {
    "running": False,
    "last_rate": None,
    "last_check": None,
    "last_trigger": None,
    "alert_history": [],
    "config": {},
    "started_at": None,
    "expired": False,
    "run_id": None # DNA do robô ativo
}


# ── Persistência no Supabase ──────────────────────────────────────────────────

def save_robot_state_to_db(config: dict, running: bool):
    """Salva a configuração do robô no Supabase para persistência."""
    try:
        supabase = get_supabase()
        data = {
            "id": "main_robot",
            "is_running": running,
            "currency": config.get("currency"),
            "min_rate": config.get("min_target"),
            "max_rate": config.get("max_target"),
            "channels": config.get("channels"),
            "expires": config.get("expires").isoformat() if isinstance(config.get("expires"), datetime) else None,
            "last_run_id": config.get("run_id"),
            "schedule_mode": config.get("schedule_mode", "hybrid"),
            "schedule_slots": config.get("schedule_slots", []),
            "maintenance_interval_h": config.get("maintenance_interval_h", 12),
            "updated_at": datetime.now().isoformat()
        }
        supabase.table("cambio_monitor_state").upsert(data).execute()
    except Exception as e:
        log.error(f"Erro ao salvar estado no Supabase: {e}")

def load_robot_state_from_db():
    """Carrega a configuração do robô do Supabase."""
    try:
        supabase = get_supabase()
        res = supabase.table("cambio_monitor_state").select("*").eq("id", "main_robot").execute()
        if res.data:
            row = res.data[0]
            if row["is_running"]:
                return {
                    "currency": row["currency"],
                    "min_target": row["min_rate"],
                    "max_target": row["max_rate"],
                    "expires": datetime.fromisoformat(row["expires"]),
                    "channels": row["channels"],
                    "run_id": row.get("last_run_id"),
                    "schedule_mode": row.get("schedule_mode", "hybrid"),
                    "schedule_slots": row.get("schedule_slots", []),
                    "maintenance_interval_h": row.get("maintenance_interval_h", 12)
                }
    except Exception as e:
        log.error(f"Erro ao carregar estado do Supabase: {e}")
    return None

def get_seconds_until_next_check(config: dict) -> int:
    """Calcula quanto tempo o robô deve esperar para a próxima verificação (Híbrido Customizado)."""
    # 1. Horários Estratégicos Escolhidos pelo Usuário
    target_slots = config.get("schedule_slots", [9.0, 10.5, 12.0, 13.0, 18.0])
    
    # 2. Ciclo de Manutenção (12h ou 24h)
    m_interval = config.get("maintenance_interval_h", 12)
    started_at_str = _robot_state.get("started_at")
    
    if started_at_str:
        try:
            start_dt = datetime.strptime(started_at_str, "%d/%m/%Y %H:%M:%S")
            start_float = start_dt.hour + start_dt.minute/60.0
            target_slots.append(start_float)
            if m_interval == 12:
                target_slots.append((start_float + 12) % 24)
        except:
            pass

    # Horário atual em Brasília (UTC-3)
    now_utc = datetime.utcnow()
    now_br  = now_utc - timedelta(hours=3)
    curr_float = now_br.hour + now_br.minute/60.0 + now_br.second/3600.0
    
    next_slot = None
    for s in sorted(list(set(target_slots))): # set para remover duplicatas
        if s > curr_float:
            next_slot = s
            break
            
    if next_slot is not None:
        diff_hours = next_slot - curr_float
    else:
        # Primeiro slot do dia seguinte
        diff_hours = (24 - curr_float) + min(target_slots)
        
    return int(max(diff_hours * 3600, 60)) # No mínimo 1 minuto de espera

def _robot_loop(config: dict):
    """Thread do robô. Executa até expirar ou ser cancelada."""
    run_id    = config.get("run_id")
    currency  = config["currency"]
    min_target = config["min_target"]
    max_target = config["max_target"]
    expires    = config["expires"]
    user_email = config.get("user_email", "")
    channels   = config.get("channels", ["In-app (painel)"])
    # Configurações dinâmicas do loop
    interval = get_seconds_until_next_check(config)
    next_check_time = (datetime.now() + timedelta(seconds=interval)).strftime("%H:%M:%S")
    
    print(f"\n[🤖 ROBÔ] Thread iniciada | ID: {run_id} | Modo: {config.get('schedule_mode','interval')}")
    print(f"[🤖 ROBÔ] Próxima verificação estimada em: {next_check_time}")

    # Garantir que expires seja naive para comparação com datetime.utcnow()
    if expires and expires.tzinfo is not None:
        expires = expires.replace(tzinfo=None)

    while datetime.utcnow() < expires:
        # CHECK DE SEGURANÇA: Se o ID mudou ou mandaram parar, encerra a thread
        with _robot_lock:
            if not _robot_state.get("running") or _robot_state.get("run_id") != run_id:
                log.warning(f"[🤖 ROBÔ] DNA inválido ou parada solicitada. Encerrando thread ({run_id})...")
                break

        try:
            rate_data = get_current_rate.__wrapped__(currency)   # bypass cache
            rate = rate_data.get("rate", 0.0)
            
            check_time = datetime.now().strftime("%H:%M:%S")
            log.warning(f"[🤖 {check_time}] {currency}/BRL: R$ {rate:.4f} | ID: {run_id}")

            with _robot_lock:
                _robot_state["last_rate"]  = rate
                _robot_state["last_check"] = datetime.now().strftime("%d/%m %H:%M:%S")
                # Não sobrescrevemos o running aqui para não atrapalhar o ID

            if rate <= min_target:
                log.warning(f"[🚨 {check_time}] MÍNIMO ATINGIDO! {rate:.4f} <= {min_target:.4f} — Disparando alerta...")
                result = dispatch_alert(currency, rate, min_target, max_target, "min", user_email, channels)
                log.warning(f"[📨 {check_time}] Resultado do dispatch: {result}")
                with _robot_lock:
                    _robot_state["last_trigger"] = f"MÍN atingido — R$ {rate:.4f}"
                    # Registrar no histórico global
                    _robot_state["alert_history"].insert(0, {
                        "time": datetime.now().strftime("%d/%m %H:%M"),
                        "currency": currency,
                        "rate": rate,
                        "trigger": "MÍN atingido"
                    })
                    _robot_state["alert_history"] = _robot_state["alert_history"][:50]

            elif rate >= max_target:
                log.warning(f"[🚨 {check_time}] MÁXIMO ATINGIDO! {rate:.4f} >= {max_target:.4f} — Disparando alerta...")
                result = dispatch_alert(currency, rate, min_target, max_target, "max", user_email, channels)
                log.warning(f"[📨 {check_time}] Resultado do dispatch: {result}")
                with _robot_lock:
                    _robot_state["last_trigger"] = f"MÁX atingido — R$ {rate:.4f}"
                    # Registrar no histórico global
                    _robot_state["alert_history"].insert(0, {
                        "time": datetime.now().strftime("%d/%m %H:%M"),
                        "currency": currency,
                        "rate": rate,
                        "trigger": "MÁX atingido"
                    })
                    _robot_state["alert_history"] = _robot_state["alert_history"][:50]
            else:
                print(f"[✅ {check_time}] Cotação dentro do intervalo. Nenhum alerta.")

        except Exception as exc:
            log.error("Robô erro: %s", exc)

        # Smart Sleep: Procura o próximo horário, mas garante que o loop rode
        interval = get_seconds_until_next_check(config)
        log.info(f"[🤖 ROBÔ] Aguardando {interval}s para próxima verificação.")
        
        slept = 0
        while slept < interval:
            time.sleep(30) # Check de parada a cada 30s
            slept += 30
            with _robot_lock:
                if not _robot_state.get("running") or _robot_state.get("run_id") != run_id:
                    return # Encerra imediatamente se o DNA mudar

    with _robot_lock:
        _robot_state["running"] = False
        _robot_state["expired"] = True
    log.info("Robô encerrado para %s.", currency)


def _start_robot(config: dict, skip_db: bool = False):
    new_run_id = str(uuid.uuid4())
    config["run_id"] = new_run_id
    
    t = threading.Thread(target=_robot_loop, args=(config,), daemon=True)
    t.start()
    with _robot_lock:
        _robot_state.update({
            "run_id":       new_run_id,
            "running":      True,
            "expired":      False,
            "last_trigger": None,
            "thread":       t,
            "config":       config,
            "last_rate":    None,
            "last_check":   None,
            "started_at":   datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        })
    if not skip_db:
        save_robot_state_to_db(config, True)


def _stop_robot():
    with _robot_lock:
        _robot_state["expired"] = True
        _robot_state["running"] = False
    save_robot_state_to_db({}, False)


# ── Render ────────────────────────────────────────────────────────────────────

def auto_recover_robot():
    """Tenta recuperar o robô do banco se ele não estiver rodando na memória."""
    with _robot_lock:
        if _robot_state.get("running"):
            return
    
    config = load_robot_state_from_db()
    if config:
        log.warning("🔄 Robô recuperado do banco de dados! Reiniciando monitoramento...")
        _start_robot(config, skip_db=True)

def render():
    # Tenta recuperar robô apenas uma vez por sessão para evitar conflito com o botão PARAR
    if not st.session_state.get("robot_recovery_checked"):
        auto_recover_robot()
        st.session_state["robot_recovery_checked"] = True
    
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
        started_at    = _robot_state.get("started_at", "—")

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
                    🕐 Iniciado em: <strong style="color:#00d4ff;">{started_at}</strong> &nbsp;|&nbsp;
                    🔄 Última atualização: <strong style="color:#f9ca24;">{last_check}</strong> &nbsp;|&nbsp;
                    💰 Cotação atual: <strong style="color:#c9d1d9;">{fmt_brl(last_rate) if last_rate else '—'}</strong>
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
                width='stretch',
                config={"displayModeBar": False},
            )

        col_stop, col_renew = st.columns(2)
        with col_stop:
            if st.button("⏹️ Parar robô", width='stretch'):
                _stop_robot()
                st.success("Robô encerrado.")
                st.rerun()
        with col_renew:
            if st.button("🔄 Renovar 24h", width='stretch'):
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
            rate_now = get_current_rate(currency).get("rate", 0.0)
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

            st.write("🔔 Canais de notificação")
            c1, c2, c3, c4 = st.columns(4)
            with c1: cb_painel = st.checkbox("💻 Painel", value=True)
            with c2: cb_wa     = st.checkbox("🟢 WhatsApp", value=True)
            with c3: cb_tg     = st.checkbox("🔵 Telegram", value=False)
            with c4: cb_email  = st.checkbox("✉️ E-mail", value=False)
            
            st.markdown("---")
            st.write("📅 **Configuração de Agenda Customizada**")
            
            cs1, cs2 = st.columns(2)
            with cs1:
                ui_m_interval = st.selectbox(
                    "Ciclo de Manutenção",
                    options=[12, 24],
                    format_func=lambda x: f"A cada {x} horas",
                    index=0,
                    help="Garante que o robô verifique a cotação pelo menos uma vez a cada ciclo, independente dos horários estratégicos."
                )
            
            with cs2:
                preset_options = {
                    "09:00 (Abertura)": 9.0,
                    "10:30 (EUA)": 10.5,
                    "12:00 (PTAX 1)": 12.0,
                    "13:00 (PTAX Final)": 13.0,
                    "18:00 (Fechamento)": 18.0,
                    "21:00 (Ajuste)": 21.0
                }
                ui_slots = st.multiselect(
                    "Horários Estratégicos",
                    options=list(preset_options.keys()),
                    default=["09:00 (Abertura)", "12:00 (PTAX 1)", "18:00 (Fechamento)"],
                    help="Momentos de maior liquidez e volatilidade no mercado (Brasília)."
                )
                selected_slots = [preset_options[s] for s in ui_slots]

            notify_channels = []
            if cb_painel: notify_channels.append("In-app (painel)")
            if cb_wa:     notify_channels.append("WhatsApp")
            if cb_tg:     notify_channels.append("Telegram")
            if cb_email:  notify_channels.append("E-mail")

            submitted = st.form_submit_button("🚀 Iniciar Monitoramento", width='stretch', type="primary")

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
                    "schedule_mode": "hybrid",
                    "schedule_slots": selected_slots,
                    "maintenance_interval_h": ui_m_interval
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

    with _robot_lock:
        alerts = _robot_state.get("alert_history", [])
        
    if not alerts:
        st.markdown(
            "<p style='color:#8892a4;font-size:0.85rem;'>Nenhum alerta disparado ainda.</p>",
            unsafe_allow_html=True,
        )
    else:
        for a in alerts[:20]:
            is_min = "min" in a["trigger"].lower()
            icon  = "📉" if is_min else "📈"
            color = "#26de81" if is_min else "#ff6b6b"
            label = a["trigger"]
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
               - Um alerta é enviado via Telegram/e-mail (se configurado)
            5. O monitoramento é válido por **24 horas**
            6. Você pode **renovar** ou **cancelar** a qualquer momento

            > ⚠️ O robô utiliza thread em background do Streamlit.
            > Para produção, considere usar Celery + Redis ou Supabase Edge Functions.
            """
        )
