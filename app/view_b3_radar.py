import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import time
from datetime import datetime
from utils.market_engine_b3 import MarketEngineB3

def render():
    st.title("🔍 Radar de Ações B3")
    
    # Inicializa o motor no cache do Streamlit
    if "engine_b3" not in st.session_state:
        st.session_state.engine_b3 = MarketEngineB3()
    
    engine = st.session_state.engine_b3

    # ── SIDEBAR CUSTOMIZADA PARA B3 ──────────────────────────────────────────
    st.sidebar.markdown("---")
    st.sidebar.subheader("⚙️ Configurações Radar B3")
    
    # Busca completa solicitada
    st.sidebar.markdown("🎯 **Análise de Ativo**")
    tickers_list = sorted(list(engine.ATIVOS.keys()))
    search_ticker = st.sidebar.selectbox(
        "Buscar ticker para o gráfico:",
        options=tickers_list,
        index=0,
        format_func=lambda t: f"{t} - {engine.DISPLAY_NAMES.get(t)}"
    )

    # Intervalo em horas/minutos solicitado
    st.sidebar.markdown("⏱️ **Frequência de Varredura**")
    col_h, col_m = st.sidebar.columns(2)
    with col_h:
        h_interval = st.number_input("Horas", 0, 24, 0, key="b3_h")
    with col_m:
        m_interval = st.number_input("Minutos", 1, 59, 5, key="b3_m")
    
    refresh_total = (h_interval * 3600) + (m_interval * 60)
    
    if st.sidebar.button("🔄 Atualizar Agora"):
        st.cache_data.clear()
        with st.spinner("Buscando dados globais..."):
            engine.tick_mercado()
        st.sidebar.success("Dados atualizados!")
        st.rerun()

    # ── SENTIMENTO GLOBAL (NYSE) ─────────────────────────────────────────────
    st.markdown("#### 🌍 Sentimento Global (B3 vs Wall Street)")
    c_sp, c_dxy, c_corr = st.columns(3)
    
    with c_sp:
        sp_val = engine.precos.get("^GSPC", 0)
        sp_var = engine.variacao.get("^GSPC", 0)
        st.metric("S&P 500 (NYSE)", f"{sp_val:,.2f}", f"{sp_var:+.2f}%")
    
    with c_dxy:
        dxy_val = engine.precos.get("DX-Y.NYB", 0)
        dxy_var = engine.variacao.get("DX-Y.NYB", 0)
        st.metric("Dólar Index (DXY)", f"{dxy_val:.2f}", f"{dxy_var:+.2f}%", delta_color="inverse")
    
    with c_corr:
        # Lógica de correlação simples para orientação
        if sp_var < -0.5:
            st.warning("⚠️ Risk-Off (Dólar ↑)")
        elif sp_var > 0.5:
            st.success("✅ Risk-On (BRL ↑)")
        else:
            st.info("⏸️ Mercado Lateral")

    # Lógica de Atualização Automática (Restaurada)
    if 'last_b3_update' not in st.session_state:
        st.session_state.last_b3_update = time.time()

    if time.time() - st.session_state.last_b3_update >= refresh_total:
        with st.spinner("Atualizando radar global..."):
            engine.tick_mercado()
        st.session_state.last_b3_update = time.time()

    # ── CONTEÚDO PRINCIPAL ───────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Mercado Real-Time",
        "📈 Gráfico Detalhado",
        "🎯 Sinais Técnicos",
        "📰 Últimas Notícias"
    ])

    # --- TAB 1: MERCADO ---
    with tab1:
        st.markdown(f"#### ⚡ Cotações Atuais (Refresca cada {refresh_total}s)")
        
        # Grid de cards (Métricas rápidas)
        cols = st.columns(4)
        tickers = list(engine.ATIVOS.keys())
        for i, t in enumerate(tickers[:8]):
            with cols[i % 4]:
                p = engine.precos.get(t, 0)
                v = engine.variacao.get(t, 0)
                st.metric(label=f"{t}", value=f"R$ {p:.2f}", delta=f"{v:+.2f}%")

        st.markdown("---")
        # Tabela Detalhada
        st.markdown("##### 📋 Tabela Geral")
        data = []
        for t in sorted(engine.ATIVOS.keys()):
            data.append({
                "Ativo": t,
                "Empresa": engine.DISPLAY_NAMES.get(t),
                "Preço": f"R$ {engine.precos.get(t,0):.2f}",
                "Variação": f"{engine.variacao.get(t,0):+.2f}%",
                "Máxima": f"R$ {engine.maximos.get(t,0):.2f}",
                "Mínima": f"R$ {engine.minimos.get(t,0):.2f}",
                "Fonte": engine.ATIVOS[t]["fonte"].upper()
            })
        st.table(data)

    # --- TAB 2: GRÁFICOS ---
    with tab2:
        st.markdown(f"#### 📈 Gráfico de Performance: {search_ticker}")
        hist = list(engine.historico[search_ticker])
        
        if hist and len(hist) > 1:
            cor = engine.ATIVOS.get(search_ticker, {}).get("cor", "#4B7BEC")
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(hist, color=cor, linewidth=2)
            ax.fill_between(range(len(hist)), hist, alpha=0.1, color=cor)
            
            # Médias Móveis se houver dados
            if len(hist) >= 20:
                mm20 = np.convolve(hist, np.ones(20)/20, mode='valid')
                ax.plot(range(19, len(hist)), mm20, "--", color="#378ADD", label="MM20")
            
            ax.set_title(f"Evolução Intradiária - {search_ticker}")
            ax.grid(True, alpha=0.2)
            st.pyplot(fig)
        else:
            st.info("Aguardando coleta de dados históricos... Clique em 'Atualizar Agora' para carregar.")

    # --- TAB 3: SINAIS ---
    with tab3:
        st.markdown("#### 🎯 Estratégia do Robô")
        cols = st.columns(2)
        for i, t in enumerate(sorted(engine.ATIVOS.keys())):
            with cols[i % 2]:
                sig, bg, fg = engine.sinal(t)
                st.markdown(f"""
                <div style='background-color: {bg}; padding: 15px; border-radius: 10px; border-left: 5px solid {fg}; margin-bottom: 10px;'>
                    <h5 style='color: {fg}; margin: 0;'>{t} - {engine.DISPLAY_NAMES[t]}</h5>
                    <p style='font-size: 1.2rem; font-weight: bold; margin: 5px 0; color: {fg};'>{sig}</p>
                    <small style='color: #666;'>Variação: {engine.variacao.get(t, 0):+.2f}%</small>
                </div>
                """, unsafe_allow_html=True)

    # --- TAB 4: NOTÍCIAS ---
    with tab4:
        st.subheader("📰 Notícias e Radar B3")
        
        from cambio_services.news_service import get_latest_market_news
        
        # Busca notícias reais focadas em B3 e Ações
        with st.spinner("Buscando notícias recentes..."):
            articles = get_latest_market_news(query="B3 ações Ibovespa mercado financeiro")
        
        if articles:
            for art in articles[:8]:
                sentiment_val = art.get("sentiment", 0)
                emoji_sent = "🟢" if sentiment_val > 0.1 else "🔴" if sentiment_val < -0.1 else "⏸️"
                cor_sent = "#26de81" if sentiment_val > 0.1 else "#ff6b6b" if sentiment_val < -0.1 else "#f9ca24"
                
                st.markdown(f"""
                <div style='background-color: #161b22; padding: 12px; border-radius: 8px; border-left: 4px solid {cor_sent}; margin-bottom: 10px; border: 1px solid #30363d;'>
                    <a href="{art['url']}" target="_blank" style="text-decoration:none; color:#c9d1d9; font-weight:600; font-size:14px;">{art['title']}</a>
                    <div style="font-size:0.75rem; color:#8892a4; margin-top:5px;">
                        {emoji_sent} Sentimento: {sentiment_val:+.2f} | Fonte: {art['source']} | {art.get('published', 'Data N/D')}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Nenhuma notícia de ações encontrada nas últimas horas.")

    st.markdown("---")
    st.caption(f"Última atualização do Radar B3: {datetime.now().strftime('%H:%M:%S')}")
