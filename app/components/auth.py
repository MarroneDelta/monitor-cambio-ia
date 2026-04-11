import streamlit as st
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

# Inicializa o cliente Supabase
@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def check_auth() -> bool:
    """Verifica se o usuário está autenticado na sessão do Streamlit."""
    return st.session_state.get("authenticated", False)

def show_login():
    """Interface de login integrada ao Supabase Auth."""
    st.markdown(
        """
        <div style="text-align:center; padding:2rem 0;">
            <div style="font-size:3.5rem; margin-bottom:1rem;">🔐</div>
            <h1 style="color:#c9d1d9; margin:0;">Monitor de Câmbio</h1>
            <p style="color:#8892a4;">Acesse sua conta para continuar</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    supabase = get_supabase()
    
    with st.form("login_form"):
        # No Supabase Auth, o login padrão é via E-mail
        email = st.text_input("E-mail")
        pwd = st.text_input("Senha", type="password")
        
        if st.form_submit_button("🚀 Entrar", width="stretch"):
            if not email or not pwd:
                st.warning("Por favor, preencha todos os campos.")
                return

            try:
                # Tenta autenticar no Supabase
                response = supabase.auth.sign_in_with_password({
                    "email": email,
                    "password": pwd
                })
                
                if response.user:
                    st.session_state.authenticated = True
                    st.session_state.user_email = response.user.email
                    st.session_state.page = "dashboard"
                    st.success("Login realizado com sucesso!")
                    st.rerun()
                else:
                    st.error("Erro desconhecido na autenticação.")
                    
            except Exception as e:
                # Trata erros comuns (senha errada, email não existe, etc.)
                error_msg = str(e)
                if "invalid login credentials" in error_msg.lower():
                    st.error("E-mail ou senha incorretos.")
                elif "email not confirmed" in error_msg.lower():
                    st.error("E-mail ainda não confirmado. Verifique sua caixa de entrada.")
                else:
                    st.error(f"Erro de autenticação: {error_msg}")
