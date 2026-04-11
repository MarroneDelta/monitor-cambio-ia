"""
pages/dashboard.py — Página principal com cotações, previsão e notícias
"""

import streamlit as st
import time
from utils.helpers import render_nav, fmt_brl, trend_badge, confidence_badge
from services.currency_service import get_all_rates, get_rate_history, get_ohlc
from services.prediction_service import get_prediction
from services.news_service import get_economic_news, aggregate_sentiment
from components.charts import line_chart, candlestick_chart, mini_sparkline
from config import CURRENCIES


def render():
    render_nav()

    st.markdown(
        "<h2 style='color:#c9d1d9;margin-bottom:0;'>📊 Dashboard</h2>"
        "<p style='color:#8892a4;font-size:0.85rem;margin-top:0;'>Cotações em tempo real · Atualização automática</p>",
        unsafe_allow_html=True,
    )

    # ── Botão de atualização manual ─────────────────────────────────────────
    col_ref, col_time = st.columns([1, 3])
    with col_ref:
        if st.button("🔄 Atualizar", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    with col_time:
        st.markdown(
            f"<small style='color:#8892a4;line-height:2.5rem;'>Última atualização: {time.strftime('%H:%M:%S')}</small>",
            unsafe_allow_html=True,
        )

    # ── Cotações ────────────────────────────────────────────────────────────
    with st.spinner("Buscando cotações..."):
        rates = get_all_rates()

    # ── Cards de cotação ────────────────────────────────────────────────────
    cols = st.columns(len(CURRENCIES))
    histories = {}

    for idx, (code, meta) in enumerate(CURRENCIES.items()):
        with cols[idx]:
            rate_data = rates[code]
            rate      = rate_data["rate"]
            history   = get_rate_history(code, hours=24)
            histories[code] = history

            prev_rate = history["rate"].iloc[-2] if len(history) > 1 else rate
            delta     = rate - prev_rate
            delta_pct = (delta / prev_rate * 100) if prev_rate else 0
            color     = "#26de81" if delta >= 0 else "#ff6b6b"
            arrow     = "▲" if delta >= 0 else "▼"
            src_badge = (
                "🟢 ao vivo" if rate_data["source"] == "live" else "🟡 demo"
            )

            sparkline_vals = list(history["rate"].tail(20))
            fig_spark = mini_sparkline(sparkline_vals, color)

            st.markdown(
                f"""
                <div class="rate-card">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <span style="font-size:1.5rem;">{meta['flag']}</span>
                        <span style="font-size:0.7rem;color:#8892a4;">{src_badge}</span>
                    </div>
                    <div style="font-size:0.9rem;color:#8892a4;margin:0.3rem 0 0.1rem;">{meta['label']}</div>
                    <div style="font-size:2rem;font-weight:700;color:#00d4ff;font-family:monospace;">
                        {fmt_brl(rate)}
                    </div>
                    <div style="font-size:0.85rem;color:{color};margin-top:0.2rem;">
                        {arrow} {abs(delta):.4f} ({delta_pct:+.2f}%)
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.plotly_chart(fig_spark, use_container_width=True, config={"displayModeBar": False})

    st.markdown("---")

    # ── Gráficos de linha ────────────────────────────────────────────────────
    st.markdown("### 📈 Histórico de Cotações")
    tabs = st.tabs([f"{CURRENCIES[c]['flag']} {c}/BRL" for c in CURRENCIES])
    for i, (code, _) in enumerate(CURRENCIES.items()):
        with tabs[i]:
            df = histories[code]
            color = "#00d4ff" if i == 0 else "#a29bfe"
            st.plotly_chart(
                line_chart(df, code, color=color, height=300),
                use_container_width=True,
                config={"displayModeBar": False},
            )

    # ── Candlestick ──────────────────────────────────────────────────────────
    with st.expander("🕯️ Gráfico de Velas (últimos 14 dias)", expanded=False):
        ohlc_tabs = st.tabs([f"{CURRENCIES[c]['flag']} {c}" for c in CURRENCIES])
        for i, (code, _) in enumerate(CURRENCIES.items()):
            with ohlc_tabs[i]:
                ohlc = get_ohlc(code)
                st.plotly_chart(
                    candlestick_chart(ohlc, code, height=300),
                    use_container_width=True,
                    config={"displayModeBar": False},
                )

    st.markdown("---")

    # ── Previsão 48h ─────────────────────────────────────────────────────────
    st.markdown("### 🔮 Previsão Inteligente (48h)")

    with st.spinner("Analisando notícias..."):
        news = get_economic_news()
    sentiment = aggregate_sentiment(news)

    pred_cols = st.columns(len(CURRENCIES))
    for idx, (code, meta) in enumerate(CURRENCIES.items()):
        with pred_cols[idx]:
            pred = get_prediction(code, histories[code], sentiment)
            st.markdown(
                f"""
                <div class="pred-card">
                    <div style="font-size:1rem;font-weight:700;color:#c9d1d9;margin-bottom:0.5rem;">
                        {meta['flag']} {code}/BRL
                    </div>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.5rem;">
                        <div class="pred-item pred-min">
                            <div style="font-size:0.7rem;color:#8892a4;">MÍN PREVISTO</div>
                            <div style="font-size:1.1rem;font-weight:700;color:#26de81;">{fmt_brl(pred['min_48h'])}</div>
                        </div>
                        <div class="pred-item pred-max">
                            <div style="font-size:0.7rem;color:#8892a4;">MÁX PREVISTO</div>
                            <div style="font-size:1.1rem;font-weight:700;color:#ff6b6b;">{fmt_brl(pred['max_48h'])}</div>
                        </div>
                    </div>
                    <div style="margin-top:0.5rem;font-size:0.8rem;color:#8892a4;">
                        Tendência: {pred['trend']} &nbsp;·&nbsp; Confiança: {confidence_badge(pred['confidence'])}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Sentimento das notícias
    sent_color = "#26de81" if sentiment > 0 else ("#ff6b6b" if sentiment < 0 else "#f9ca24")
    sent_label = "Positivo 📈" if sentiment > 0 else ("Negativo 📉" if sentiment < 0 else "Neutro →")
    st.markdown(
        f"<p style='font-size:0.8rem;color:#8892a4;'>Sentimento das notícias: "
        f"<span style='color:{sent_color};font-weight:600;'>{sent_label}</span> "
        f"({sentiment:+.2f})</p>",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # ── Notícias ─────────────────────────────────────────────────────────────
    st.markdown("### 📰 Notícias Econômicas")
    with st.expander("Ver notícias recentes", expanded=False):
        for art in news[:6]:
            s = art.get("sentiment", 0)
            s_color = "#26de81" if s > 0 else ("#ff6b6b" if s < 0 else "#f9ca24")
            s_icon  = "📈" if s > 0 else ("📉" if s < 0 else "➡️")
            st.markdown(
                f"""
                <div class="news-item">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:0.5rem;">
                        <div>
                            <a href="{art['url']}" target="_blank"
                               style="color:#58a6ff;text-decoration:none;font-size:0.9rem;font-weight:600;">
                                {art['title']}
                            </a>
                            <div style="font-size:0.75rem;color:#8892a4;margin-top:0.2rem;">
                                {art['source']} · {art['published']}
                            </div>
                        </div>
                        <span style="color:{s_color};font-size:1rem;flex-shrink:0;">{s_icon}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
