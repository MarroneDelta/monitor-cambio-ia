"""
utils/math_utils.py — Análise de câmbio via OpenAI GPT-4.1-mini
"""

import logging
import json
import streamlit as st
from openai import OpenAI
from config import OPENAI_API_KEY

log = logging.getLogger(__name__)

_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

PROMPT_TEMPLATE = """Você é um analista financeiro especializado em mercado de câmbio (Forex), com foco em decisões baseadas em dados reais e notícias econômicas recentes.

Com base nos dados abaixo:
USD/BRL: R$ {valor_usd}
EUR/BRL: R$ {valor_eur}

Analise a tendência futura do USD e EUR considerando:

- Taxas de juros (FED e BCE)
- Inflação
- Cenário macroeconômico global
- Riscos geopolíticos
- Notícias econômicas recentes relevantes (ex: decisões de bancos centrais, dados de emprego, PIB, inflação, crises ou eventos globais)

Retorne de forma clara, técnica e objetiva:

1. Tendência do USD (alta, queda ou lateral)
2. Tendência do EUR (alta, queda ou lateral)
3. Comparação direta (qual moeda está mais forte)
4. Principais fatores (baseados em fatos e notícias)
5. Resumo final em até 3 linhas

⚠️ Regras importantes:
- Priorize clareza e objetividade
- Evite suposições vagas ou genéricas
- Baseie-se em lógica de mercado real e notícias econômicas plausíveis
- Não invente dados específicos; use análise fundamentada
- Limite total da resposta a no máximo 1000 tokens (preferencialmente menos)

Além do texto, retorne no FINAL da resposta um bloco JSON entre as tags <JSON> e </JSON> com esta estrutura exata:
<JSON>
{{
  "usd_trend": "alta" ou "queda" ou "lateral",
  "eur_trend": "alta" ou "queda" ou "lateral",
  "usd_min": valor_float,
  "usd_max": valor_float,
  "eur_min": valor_float,
  "eur_max": valor_float,
  "confidence": "alta" ou "média" ou "baixa"
}}
</JSON>
"""


@st.cache_data(ttl=43200, persist="disk")
def get_ai_analysis(valor_usd: float, valor_eur: float) -> dict:
    """
    Chama a OpenAI GPT-4.1-mini para análise de câmbio.
    Arredondamos os valores para 3 casas para evitar que micro-variações de 
    centavos invalidem o cache desnecessariamente.
    """
    v_usd = round(valor_usd, 3)
    v_eur = round(valor_eur, 3)
    if not _client:
        log.warning("OpenAI não configurada (OPENAI_API_KEY vazia)")
        return _fallback(valor_usd, valor_eur)

    prompt = PROMPT_TEMPLATE.format(valor_usd=f"{valor_usd:.4f}", valor_eur=f"{valor_eur:.4f}")

    try:
        print("[🤖 OpenAI] Consultando GPT-4.1-mini para análise de câmbio...")
        response = _client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "Você é um analista financeiro especialista em câmbio."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1000,
            temperature=0.4,
        )

        text = response.choices[0].message.content
        print(f"[✅ OpenAI] Análise recebida ({len(text)} chars)")

        # Extrai JSON estruturado da resposta
        data = _extract_json(text)
        data["text"] = _clean_text(text)
        data["source"] = "gpt-4.1-mini"
        return data

    except Exception as exc:
        log.error("Erro OpenAI: %s", exc)
        print(f"[❌ OpenAI] Erro: {exc}")
        return _fallback(valor_usd, valor_eur)


def _extract_json(text: str) -> dict:
    """Extrai o bloco JSON da resposta da IA."""
    try:
        start = text.index("<JSON>") + 6
        end = text.index("</JSON>")
        raw = text[start:end].strip()
        return json.loads(raw)
    except (ValueError, json.JSONDecodeError):
        return {
            "usd_trend": "lateral",
            "eur_trend": "lateral",
            "usd_min": 0, "usd_max": 0,
            "eur_min": 0, "eur_max": 0,
            "confidence": "baixa",
        }


def _clean_text(text: str) -> str:
    """Remove o bloco JSON do texto para exibição."""
    try:
        start = text.index("<JSON>")
        return text[:start].strip()
    except ValueError:
        return text.strip()


def _fallback(valor_usd: float, valor_eur: float) -> dict:
    """Fallback caso a OpenAI não esteja disponível."""
    return {
        "text": "⚠️ Análise indisponível. Configure a chave OPENAI_API_KEY no arquivo .env.",
        "source": "fallback",
        "usd_trend": "lateral",
        "eur_trend": "lateral",
        "usd_min": valor_usd * 0.99,
        "usd_max": valor_usd * 1.01,
        "eur_min": valor_eur * 0.99,
        "eur_max": valor_eur * 1.01,
        "confidence": "baixa",
    }


# Mantém compatibilidade com código legado que ainda chama get_forecast
def get_forecast(historical_prices, news_sentiment=0, projection_steps=2):
    """Compatibilidade: retorna dados mínimos para não quebrar chamadas antigas."""
    if not historical_prices:
        return None
    last = historical_prices[-1]
    return {
        "min": last * 0.99,
        "max": last * 1.01,
        "trend": "lateral",
        "confidence": "média",
        "r2": 0,
        "slope": 0,
        "diff": 0,
        "diff_pct": 0,
    }
