# 💱 Monitor de Câmbio

> Plataforma profissional de monitoramento de câmbio em tempo real com robô automático de alertas, previsão inteligente e suporte a PWA (Progressive Web App).

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-FF4B4B?logo=streamlit&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![PWA](https://img.shields.io/badge/PWA-Ready-5A0FC8?logo=pwa&logoColor=white)

---

## 📋 Índice

- [Visão Geral](#visão-geral)
- [Funcionalidades](#funcionalidades)
- [Tecnologias](#tecnologias)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Como Rodar Localmente](#como-rodar-localmente)
- [Variáveis de Ambiente](#variáveis-de-ambiente)
- [Como Subir no GitHub](#como-subir-no-github)
- [Deploy em Produção](#deploy-em-produção)
- [Credenciais Padrão](#credenciais-padrão)
- [Segurança](#segurança)

---

## 🎯 Visão Geral

O **Monitor de Câmbio** é uma aplicação web full-stack construída com Python + Streamlit que permite:

- Acompanhar cotações de **Dólar (USD)** e **Euro (EUR)** em tempo real
- Visualizar histórico e gráficos interativos (linha e candlestick)
- Obter **previsão heurística** para as próximas 48h com análise de sentimento de notícias
- Configurar um **robô automático** que monitora a cotação e dispara alertas quando atinge mínimo ou máximo definido
- Receber notificações via **Telegram**, **e-mail** ou painel in-app
- Instalar como **app no celular** (PWA — Android e iOS)

---

## ✨ Funcionalidades

### 📊 Dashboard
- Cotação em tempo real de USD/BRL e EUR/BRL
- Cards com variação percentual e sparklines
- Gráfico de linha (histórico 24h)
- Gráfico de velas (OHLC 14 dias)
- Indicador de tendência (alta/queda/estável)

### 🔮 Previsão Inteligente
- Projeção de mínimo e máximo para as próximas 48h
- Análise de sentimento de notícias econômicas
- Indicador de confiança da previsão

### 🤖 Câmbio Auto (Robô)
- Configure valor mínimo e máximo desejado
- Monitoramento em background (thread)
- Verificação automática a cada 5 minutos
- Válido por 24h (renovável)
- Histórico de alertas disparados

### 🔔 Notificações
- **In-app**: histórico visível no painel
- **Telegram Bot**: mensagem instantânea
- **E-mail SMTP**: suporte a Gmail e outros

### 📱 PWA
- Instalável como app no Android e iOS
- Service Worker com cache offline parcial
- Theme color e manifest configurados

---

## 🛠️ Tecnologias

| Categoria | Tecnologia |
|-----------|-----------|
| Framework Web | Streamlit 1.35+ |
| Linguagem | Python 3.11+ |
| Gráficos | Plotly 5+ |
| Dados | Pandas 2+ |
| Segurança | bcrypt, python-dotenv |
| HTTP | requests |
| Notificações | Telegram Bot API, smtplib |
| PWA | manifest.json + Service Worker |
| API Câmbio | AwesomeAPI (gratuita) + ExchangeRate-API |
| API Notícias | NewsAPI + Google News RSS |

---

## 📁 Estrutura do Projeto

```
cambio_app/
├── app/
│   ├── main.py                   # Ponto de entrada Streamlit
│   ├── config.py                 # Configurações e constantes
│   ├── __init__.py
│   ├── pages/
│   │   ├── dashboard.py          # Página principal
│   │   └── cambio_auto.py        # Robô de monitoramento
│   ├── components/
│   │   ├── auth.py               # Login, logout, sessão
│   │   ├── charts.py             # Gráficos Plotly
│   │   └── notifications.py      # Telegram, e-mail, in-app
│   ├── services/
│   │   ├── currency_service.py   # APIs de câmbio
│   │   ├── prediction_service.py # Previsão heurística
│   │   └── news_service.py       # Notícias + sentimento
│   ├── utils/
│   │   ├── security.py           # bcrypt, sanitização
│   │   └── helpers.py            # CSS, PWA, formatação
│   └── assets/
│       ├── styles.css            # CSS dark mobile-first
│       ├── manifest.json         # PWA manifest
│       └── service_worker.js     # Service Worker
├── .streamlit/
│   └── config.toml               # Tema dark + configurações
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 🚀 Como Rodar Localmente

### Pré-requisitos
- Python 3.11 ou superior
- pip atualizado

### Passo a passo

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/monitor-cambio.git
cd monitor-cambio

# 2. Crie e ative o ambiente virtual
python -m venv venv

# Linux/macOS
source venv/bin/activate

# Windows
venv\Scripts\activate

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure as variáveis de ambiente
cp .env.example .env
# Edite o .env com suas chaves (opcional — funciona sem elas no modo demo)

# 5. Rode a aplicação
cd app
streamlit run main.py
```

Acesse: **http://localhost:8501**

---

## 🔑 Variáveis de Ambiente

Copie `.env.example` para `.env` e preencha:

| Variável | Descrição | Obrigatório |
|----------|-----------|-------------|
| `EXCHANGE_API_KEY` | Chave da [ExchangeRate-API](https://exchangerate-api.com) | Não (usa AwesomeAPI grátis) |
| `NEWS_API_KEY` | Chave da [NewsAPI](https://newsapi.org) | Não (usa RSS gratuito) |
| `TELEGRAM_TOKEN` | Token do Bot Telegram | Não (alertas in-app funcionam) |
| `TELEGRAM_CHAT_ID` | ID do chat Telegram | Não |
| `SMTP_HOST` | Servidor SMTP (ex: smtp.gmail.com) | Não |
| `SMTP_PORT` | Porta SMTP (587) | Não |
| `SMTP_USER` | E-mail remetente | Não |
| `SMTP_PASSWORD` | Senha de app do e-mail | Não |
| `ADMIN_EMAIL` | E-mail do admin para alertas | Não |

> ✅ **A aplicação funciona em modo demo sem nenhuma variável configurada.**
> As cotações usarão a AwesomeAPI (gratuita, sem chave) e notificações serão apenas in-app.

---

## 📤 Como Subir no GitHub

```bash
# Inicialize o repositório (se ainda não fez)
git init
git add .
git commit -m "feat: Monitor de Câmbio v1.0"

# Crie o repositório no GitHub (via CLI ou interface web)
# Com GitHub CLI:
gh repo create monitor-cambio --public --push --source=.

# OU conecte a um repositório existente:
git remote add origin https://github.com/seu-usuario/monitor-cambio.git
git branch -M main
git push -u origin main
```

> ⚠️ Verifique que o arquivo `.env` **não está** sendo commitado (está no `.gitignore`).

---

## ☁️ Deploy em Produção

### Streamlit Community Cloud (gratuito)

1. Faça push do código para o GitHub
2. Acesse [share.streamlit.io](https://share.streamlit.io)
3. Conecte seu repositório
4. Defina **Main file path**: `app/main.py`
5. Em **Advanced settings → Secrets**, adicione suas variáveis do `.env`
6. Clique em **Deploy**

### Railway / Render / Fly.io

```bash
# Procfile (Railway/Render)
echo "web: streamlit run app/main.py --server.port=\$PORT --server.address=0.0.0.0" > Procfile
```

Adicione as variáveis de ambiente no painel da plataforma escolhida.

---

## 🔐 Credenciais Padrão

| Usuário | Senha | Perfil |
|---------|-------|--------|
| `admin` | `admin123` | Administrador |
| `usuario` | `demo123` | Demo |

> ⚠️ **Altere as senhas antes de usar em produção!**
>
> Para gerar um novo hash bcrypt:
> ```bash
> cd app
> python -c "from utils.security import hash_password; print(hash_password('nova_senha'))"
> ```
> Substitua o `password_hash` correspondente em `config.py`.

---

## 🛡️ Segurança

- ✅ Senhas armazenadas com **bcrypt** (rounds=12)
- ✅ Sanitização de inputs contra XSS
- ✅ Chaves de API em variáveis de ambiente
- ✅ Sessão com expiração automática (8h)
- ✅ Proteção XSRF habilitada no Streamlit
- ✅ CORS desabilitado por padrão
- ✅ `.env` no `.gitignore`
- ✅ Logs sem exposição de chaves

---

## 📄 Licença

MIT License — use e modifique livremente.

---

*Desenvolvido com ❤️ em Python + Streamlit*
