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
        st.metric("S&P 500 (NYSE)", f"{sp_val:,.2f}" if sp_val > 0 else "---", f"{sp_var:+.2f}%" if sp_val > 0 else None)
    
    with c_dxy:
        dxy_val = engine.precos.get("DXY", 0)
        dxy_var = engine.variacao.get("DXY", 0)
        st.metric("Dólar Index (DXY)", f"{dxy_val:.2f}" if dxy_val > 0 else "---", f"{dxy_var:+.2f}%" if dxy_val > 0 else None, delta_color="inverse")
    
    with c_corr:
        # Lógica Profissional de Sentimento Global (Risk-On / Risk-Off)
        if sp_var < -0.5:
            sentiment_type = "OFF"
            title = "Cautela (Risk-Off)"
            desc = "Mercado Global em modo defensivo. Capital fugindo para o porto seguro do Dólar."
            glow_color = "#E24B4A" # Vermelho
            bg_color = "rgba(226, 75, 74, 0.05)"
        elif sp_var > 0.5:
            sentiment_type = "ON"
            title = "Otimismo (Risk-On)"
            desc = "Fluxo favorável para ativos de risco. Capital entrando no Brasil e na B3."
            glow_color = "#1D9E75" # Verde
            bg_color = "rgba(29, 158, 117, 0.05)"
        else:
            sentiment_type = "NEUTRO"
            title = "Expectativa (Lateral)"
            desc = "Mercado aguardando sinais mais fortes. Estabilidade momentânea."
            glow_color = "#378ADD" # Azul
            bg_color = "rgba(55, 138, 221, 0.05)"

        # Card Premium Customizado em HTML/CSS
        st.markdown(f"""
            <style>
                @keyframes pulse-glow {{ 0% {{ box-shadow: 0 0 5px {glow_color}33; }} 50% {{ box-shadow: 0 0 20px {glow_color}66; }} 100% {{ box-shadow: 0 0 5px {glow_color}33; }} }}
                .premium-card {{
                    background: {bg_color};
                    backdrop-filter: blur(10px);
                    border: 1px solid {glow_color}55;
                    border-radius: 12px;
                    padding: 15px;
                    height: 120px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    animation: pulse-glow 3s infinite ease-in-out;
                    transition: all 0.3s ease;
                }}
                .premium-title {{ color: {glow_color}; font-size: 0.85rem; font-weight: 700; text-transform: uppercase; margin-bottom: 5px; display: flex; align-items: center; gap: 8px; }}
                .premium-desc {{ color: #D3D1C7; font-size: 0.75rem; line-height: 1.3; margin: 0; }}
            </style>
            <div class="premium-card">
                <div class="premium-title">
                    <span>🧠 INSIGHT DE MERCADO</span>
                </div>
                <h6 style="color:white; margin:0 0 5px 0; font-size: 1rem;">{title}</h6>
                <p class="premium-desc">{desc}</p>
            </div>
        """, unsafe_allow_html=True)

    # Guia de Especialista (Expander Premium)
    with st.expander("🎓 Como o Segredo dos Grandes Investidores funciona?"):
        st.markdown(f"""
        <div style="font-size: 0.85rem; color: #888780;">
            O <b>Sentimento Global</b> é o motor que move o câmbio. 
            <br><br>
            • <b>Risk-On:</b> Quando o S&P 500 (EUA) sobe, o mundo está otimista. Investidores vendem Dólar para comprar ações e moedas de países emergentes como o Brasil. Isso faz o nosso Dólar cair e a nossa Bolsa subir.
            <br><br>
            • <b>Risk-Off:</b> Quando o S&P 500 cai e o Dólar Global (DXY) sobe, o mercado está com medo. O dinheiro foge para a segurança dos EUA, o que pressiona o nosso Dólar para cima e a nossa Bolsa para baixo.
        </div>
        """, unsafe_allow_html=True)

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
        
        # Grid de cards (Design Customizado Premium - Corrigido Sem Indentação)
        tickers = list(engine.ATIVOS.keys())
        radar_html = """<style>
.radar-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
}
.asset-card {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(211, 209, 199, 0.1);
    border-radius: 12px;
    padding: 20px;
    transition: all 0.3s ease;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}
.asset-card:hover {
    transform: translateY(-5px);
    background: rgba(255, 255, 255, 0.05);
    border-color: rgba(55, 138, 221, 0.4);
    box-shadow: 0 10px 20px rgba(0,0,0,0.2);
}
.asset-ticker {
    color: #8892a4;
    font-size: 0.8rem;
    font-weight: 600;
    margin-bottom: 5px;
}
.asset-price {
    color: white;
    font-size: 1.4rem;
    font-weight: 700;
    margin: 5px 0;
}
.asset-var {
    font-size: 0.85rem;
    font-weight: 600;
}
.var-up { color: #1D9E75; }
.var-down { color: #E24B4A; }
</style>
<div class="radar-grid">"""
        
        for t in tickers[:8]:
            p = engine.precos.get(t, 0)
            v = engine.variacao.get(t, 0)
            var_class = "var-up" if v >= 0 else "var-down"
            icon = "▲" if v >= 0 else "▼"
            
            radar_html += f'<div class="asset-card"><div class="asset-ticker">{t}</div><div class="asset-price">R$ {p:,.2f}</div><div class="asset-var {var_class}">{icon} {abs(v):.2f}%</div></div>'
        
        radar_html += '</div>'
        st.markdown(radar_html, unsafe_allow_html=True)

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
        st.markdown("#### 🎯 Estratégia do Robô de Elite")
        st.caption("Baseado em Médias Móveis (MM20/MM50) e Volatilidade de 30 dias")
        
        cols = st.columns(2)
        for i, t in enumerate(sorted(engine.ATIVOS.keys())):
            with cols[i % 2]:
                sig, bg, fg = engine.sinal(t)
                v = engine.variacao.get(t, 0)
                
                # Ícone dinâmico baseado no sinal
                icon = "🚀" if sig == "COMPRA" else "🎯" if sig == "REALIZAR" else "🛡️" if sig == "ATENÇÃO" else "⏸️"
                
                # Card Premium Estilizado
                st.markdown(f"""
                <div style='
                    background: rgba(255, 255, 255, 0.02);
                    backdrop-filter: blur(10px);
                    padding: 20px;
                    border-radius: 15px;
                    border: 1px solid {fg}44;
                    border-left: 6px solid {fg};
                    margin-bottom: 20px;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                    transition: transform 0.2s;
                '>
                    <div style='display: flex; justify-content: space-between; align-items: center;'>
                        <span style='color: #888780; font-size: 0.8rem; font-weight: 600;'>{t}</span>
                        <span style='background: {fg}22; color: {fg}; padding: 2px 8px; border-radius: 20px; font-size: 0.7rem; font-weight: bold;'>B3 ACTIVE</span>
                    </div>
                    <h5 style='color: white; margin: 10px 0 5px 0; font-size: 1.1rem;'>{engine.DISPLAY_NAMES[t]}</h5>
                    <div style='display: flex; align-items: center; gap: 10px; margin: 15px 0;'>
                        <span style='font-size: 1.8rem;'>{icon}</span>
                        <div style='display: flex; flex-direction: column;'>
                            <span style='color: {fg}; font-size: 1.2rem; font-weight: 800; letter-spacing: 1px;'>{sig}</span>
                            <span style='color: {"#26de81" if v >= 0 else "#ff6b6b"}; font-size: 0.85rem; font-weight: 600;'>Var. Dia: {v:+.2f}%</span>
                        </div>
                    </div>
                    <div style='border-top: 1px solid rgba(255,255,255,0.05); padding-top: 10px; margin-top: 10px;'>
                        <small style='color: #5F5E5A; font-style: italic;'>Sugestão do robô baseada em tendência de curto prazo.</small>
                    </div>
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
