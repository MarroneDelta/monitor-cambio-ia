"""
views/dashboard.py — Página principal com cotações e análise
"""

import streamlit as st
import pandas as pd
import time
from cambio_services.currency_service import get_current_rate, get_ohlc, get_rate_history
from cambio_services.news_service import get_latest_market_news, aggregate_sentiment
from components.charts import line_chart, candlestick_chart
from utils.helpers import render_nav, fmt_brl, trend_badge, confidence_badge, sentiment_badge
from utils.math_utils import get_forecast
from config import APP_CONFIG


def render():
    # Header + botão atualizar
    h_col, btn_col = st.columns([4, 1])
    with h_col:
        st.markdown(
            "<h2 style='color:#c9d1d9;margin-bottom:0;'>📊 Dashboard</h2>"
            "<p style='color:#8892a4;font-size:0.85rem;margin-top:0;'>Cotações em tempo real · Atualização automática</p>",
            unsafe_allow_html=True
        )
    with btn_col:
        if st.button("🔄 Atualizar", key="btn_refresh", width="stretch", type="primary"):
            # ✅ Sem limpeza de cache - deixar Streamlit gerenciar
            st.session_state.pop("engine_b3", None)
            # Force refresh das cotações
            from cambio_services.currency_service import get_current_rate as get_rate
            get_rate.__wrapped__("USD")  # Contorna cache
            get_rate.__wrapped__("EUR")
            st.rerun()
    
    # Cards de resumo
    render_summary_cards()
    
    # Gráfico de velas
    render_candles()
    
    # Previsão inteligente
    render_intelligent_forecast()
    
    # Notícias
    render_news_section()
    
    # Auto-refresh
    if st.session_state.get("auto_refresh", True):
        time.sleep(1) # Pequeno delay antes de agendar
        # O Streamlit rerun acontece no final do ciclo se necessário


def render_summary_cards():
    c1, c2 = st.columns(2)
    
    for currency, col in zip(["USD", "EUR"], [c1, c2]):
        with col:
            res = get_current_rate(currency)
            if res:
                rate = res.get("rate", 0.0)
                change = res.get("change_pct", 0.0)
                trend_icon = "↑" if change >= 0 else "↓"
                
                # Salva no session state para a previsão
                st.session_state[f"rate_{currency}/BRL"] = rate
                
                color = "#26de81" if change >= 0 else "#ff6b6b"
                icon = "🟢" if change >= 0 else "🔴"
                
                with st.container():
                    st.markdown(
                        f"""
                        <div class="robot-status-card" style="margin-bottom:1rem;">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <span style="font-size:0.8rem; color:#8892a4;">{icon} AO VIVO</span>
                                <span style="font-size:0.8rem; color:#8892a4;">{res.get('currency_name', currency)}</span>
                            </div>
                            <h2 style="margin:10px 0; font-size:2rem;">R$ {rate:.4f}</h2>
                            <div style="color:{color}; font-size:0.9rem; font-weight:600;">
                                {trend_icon} {change:+.2f}%
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    # Mini gráfico de linha (Sparkline)
                    hist = get_rate_history(currency, hours=24)
                    if hist is not None and not hist.empty:
                        fig = line_chart(hist, f"{currency}/BRL", height=100)
                        st.plotly_chart(fig, width="stretch", config={'displayModeBar': False})


def render_candles():
    with st.expander("🕯️ Gráfico de Velas (últimos 14 dias)", expanded=False):
        for currency in ["USD", "EUR"]:
            hist_data = get_ohlc(currency, days=14)
            if hist_data is not None and not hist_data.empty:
                st.subheader(f"Histórico {currency}/BRL")
                fig_candle = candlestick_chart(hist_data, f"{currency}/BRL")
                st.plotly_chart(fig_candle, width="stretch")


def render_intelligent_forecast():
    st.markdown("### 🤖 Análise de Câmbio via IA (Correlação NYSE/B3)")
    
    from utils.math_utils import get_ai_analysis
    from utils.market_engine_b3 import MarketEngineB3
    
    if "engine_b3" not in st.session_state:
        st.session_state.engine_b3 = MarketEngineB3()
    engine = st.session_state.engine_b3
    
    # Coleta dados globais para a IA
    sp500 = engine.precos.get("^GSPC", 0)
    dxy = engine.precos.get("DX=F", 0)
    
    usd_data = get_current_rate("USD")
    eur_data = get_current_rate("EUR")
    valor_usd = usd_data.get("rate", 0.0)
    valor_eur = eur_data.get("rate", 0.0)
    
    # Lógica de IA SOB DEMANDA (Manual)
    if "last_ai_analysis" not in st.session_state:
        st.info("💡 Clique no botão abaixo para gerar uma análise profunda do mercado com IA.")
        if st.button("🧠 Gerar Análise de Mercado (IA)", type="secondary"):
            with st.spinner("IA analisando contexto global... (esta ação consome créditos)"):
                analysis = get_ai_analysis(round(valor_usd, 3), round(valor_eur, 3), sp500=sp500, dxy=dxy)
                st.session_state.last_ai_analysis = analysis
                st.rerun()
        return # Interrompe a renderização desta seção se não houver análise

    analysis = st.session_state.last_ai_analysis
    
    # Botão para atualizar a análise existente
    if st.button("🔄 Atualizar Análise IA", help="Gera uma nova análise baseada nos preços atuais"):
        with st.spinner("Atualizando análise..."):
            analysis = get_ai_analysis(round(valor_usd, 3), round(valor_eur, 3), sp500=sp500, dxy=dxy)
            st.session_state.last_ai_analysis = analysis
            st.rerun()
    
    # Cards de tendência (compactos)
    c1, c2 = st.columns(2)
    trend_colors = {"alta": "#26de81", "queda": "#ff6b6b", "lateral": "#f9ca24"}
    trend_icons = {"alta": "📈", "queda": "📉", "lateral": "➡️"}
    
    for currency, col, trend_key, min_key, max_key in [
        ("USD", c1, "usd_trend", "usd_min", "usd_max"),
        ("EUR", c2, "eur_trend", "eur_min", "eur_max"),
    ]:
        with col:
            trend = analysis.get(trend_key, "lateral")
            color = trend_colors.get(trend, "#f9ca24")
            icon = trend_icons.get(trend, "➡️")
            flag = "💵" if currency == "USD" else "💶"
            min_val = analysis.get(min_key, 0)
            max_val = analysis.get(max_key, 0)
            
            st.markdown(
                f"""<div style="background:#161b22;border-radius:10px;padding:0.8rem;border-left:4px solid {color};">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <span style="font-weight:700;color:#c9d1d9;">{flag} {currency}/BRL</span>
                        <span style="font-size:1.1rem;font-weight:700;color:{color};">{icon} {trend.upper()}</span>
                    </div>
                    <div style="display:flex;gap:1.5rem;margin-top:0.5rem;">
                        <div><span style="font-size:0.7rem;color:#8892a4;">MÍN</span><br><span style="color:#26de81;font-weight:600;">R$ {min_val:.4f}</span></div>
                        <div><span style="font-size:0.7rem;color:#8892a4;">MÁX</span><br><span style="color:#ff6b6b;font-weight:600;">R$ {max_val:.4f}</span></div>
                    </div>
                </div>""",
                unsafe_allow_html=True,
            )
    
    # Análise textual (compacta)
    confidence = analysis.get("confidence", "média")
    source = analysis.get("source", "IA")
    if source == "gpt-4.1-mini":
        source = "Inteligência Artificial"
    
    st.markdown(
        f"""<div style="background:#161b22;border-radius:10px;padding:1rem;border:1px solid #30363d;margin-top:0.5rem;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;">
                <span style="font-weight:700;color:#c9d1d9;">📋 Análise Completa</span>
                <span style="font-size:0.7rem;background:#00d4ff22;color:#00d4ff;padding:2px 8px;border-radius:10px;">
                    {source} · {confidence}
                </span>
            </div>
            <div style="color:#c9d1d9;font-size:0.85rem;line-height:1.6;white-space:pre-wrap;">{analysis.get('text', 'Sem análise disponível.')}</div>
        </div>""",
        unsafe_allow_html=True,
    )
    
    # Card: Valor Atual → Previsão 24h
    usd_prev = (analysis.get("usd_min", valor_usd) + analysis.get("usd_max", valor_usd)) / 2
    eur_prev = (analysis.get("eur_min", valor_eur) + analysis.get("eur_max", valor_eur)) / 2
    usd_diff = usd_prev - valor_usd
    eur_diff = eur_prev - valor_eur
    usd_color = "#26de81" if usd_diff >= 0 else "#ff6b6b"
    eur_color = "#26de81" if eur_diff >= 0 else "#ff6b6b"
    usd_arrow = "▲" if usd_diff >= 0 else "▼"
    eur_arrow = "▲" if eur_diff >= 0 else "▼"
    
    st.markdown(
        f"""<div style="background:linear-gradient(135deg,#161b22,#1a1f2e);border-radius:10px;padding:1rem;margin-top:0.5rem;border:1px solid #30363d;">
            <div style="font-weight:700;color:#c9d1d9;margin-bottom:0.6rem;">💱 Cotação Atual → Previsão 24h</div>
            <div style="display:flex;gap:2rem;flex-wrap:wrap;">
                <div style="flex:1;min-width:200px;">
                    <div style="font-size:0.75rem;color:#8892a4;">💵 USD/BRL</div>
                    <div style="display:flex;align-items:center;gap:0.5rem;margin-top:0.3rem;">
                        <span style="font-size:1.1rem;color:#c9d1d9;font-weight:700;">R$ {valor_usd:.4f}</span>
                        <span style="color:#8892a4;">→</span>
                        <span style="font-size:1.1rem;color:{usd_color};font-weight:700;">R$ {usd_prev:.4f}</span>
                        <span style="font-size:0.8rem;color:{usd_color};font-weight:600;">{usd_arrow} {usd_diff:+.4f}</span>
                    </div>
                </div>
                <div style="flex:1;min-width:200px;">
                    <div style="font-size:0.75rem;color:#8892a4;">💶 EUR/BRL</div>
                    <div style="display:flex;align-items:center;gap:0.5rem;margin-top:0.3rem;">
                        <span style="font-size:1.1rem;color:#c9d1d9;font-weight:700;">R$ {valor_eur:.4f}</span>
                        <span style="color:#8892a4;">→</span>
                        <span style="font-size:1.1rem;color:{eur_color};font-weight:700;">R$ {eur_prev:.4f}</span>
                        <span style="font-size:0.8rem;color:{eur_color};font-weight:600;">{eur_arrow} {eur_diff:+.4f}</span>
                    </div>
                </div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )




def render_news_section():
    st.markdown("---")
    st.markdown("### 📰 Últimas Notícias Econômicas")
    
    from cambio_services.news_service import get_latest_market_news
    articles = get_latest_market_news()
    if articles:
        for art in articles[:5]:  # Top 5 notícias
            with st.container():
                st.markdown(
                    f"""
                    <div style="padding:10px; border-radius:8px; background:#161b22; margin-bottom:10px; border-left:4px solid #00d4ff;">
                        <a href="{art['url']}" target="_blank" style="text-decoration:none; color:#c9d1d9; font-weight:600;">{art['title']}</a>
                        <div style="font-size:0.75rem; color:#8892a4; margin-top:5px;">
                            Fonte: {art['source']} | {art.get('published', 'Data N/D')}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
    else:
        st.info("Nenhuma notícia relevante encontrada no momento.")
