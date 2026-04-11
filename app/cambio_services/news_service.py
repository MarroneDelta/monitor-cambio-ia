"""
services/news_service.py — Notícias econômicas + análise de sentimento simples
"""

import logging
import re
from typing import List, Dict, Optional
import streamlit as st
import requests

from config import NEWS_API_KEY

log = logging.getLogger(__name__)

_POSITIVE_WORDS = {
    "alta", "subiu", "cresceu", "valoriz", "ganho", "lucro", "positiv",
    "recorde", "superávit", "crescimento", "melhora", "recover",
    "rise", "gain", "positive", "growth", "strong",
}
_NEGATIVE_WORDS = {
    "queda", "caiu", "baixou", "desvaloriza", "perda", "risco", "negativ",
    "déficit", "recessão", "crise", "inflação", "war", "conflict",
    "fall", "drop", "negative", "weak", "recession",
}


def _simple_sentiment(text: str) -> float:
    """Retorna valor entre -1 (negativo) e +1 (positivo)."""
    text_lower = text.lower()
    pos = sum(1 for w in _POSITIVE_WORDS if w in text_lower)
    neg = sum(1 for w in _NEGATIVE_WORDS if w in text_lower)
    total = pos + neg
    if total == 0:
        return 0.0
    return round((pos - neg) / total, 2)


@st.cache_data(ttl=43200, show_spinner=False)
def get_economic_news(query: str = "dólar euro câmbio economia") -> List[Dict]:
    articles = _fetch_newsapi(query) or _fetch_rss_fallback()
    for art in articles:
        text = art.get("title", "") + " " + art.get("description", "")
        art["sentiment"] = _simple_sentiment(text)
    return articles[:10]


def _fetch_newsapi(query: str) -> Optional[List[Dict]]:
    if not NEWS_API_KEY:
        return None
    try:
        r = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": query,
                "language": "pt",
                "sortBy": "publishedAt",
                "pageSize": 10,
                "apiKey": NEWS_API_KEY,
            },
            timeout=8,
        )
        if r.status_code == 200:
            return [
                {
                    "title":       a.get("title", ""),
                    "description": a.get("description", ""),
                    "url":         a.get("url", ""),
                    "source":      a.get("source", {}).get("name", ""),
                    "published":   a.get("publishedAt", "")[:10],
                }
                for a in r.json().get("articles", [])
                if a.get("title")
            ]
    except Exception as exc:
        log.warning("NewsAPI falhou: %s", exc)
    return None


def _fetch_rss_fallback() -> List[Dict]:
    """Notícias do Google News RSS como fallback (sem chave)."""
    try:
        from xml.etree import ElementTree as ET
        r = requests.get(
            "https://news.google.com/rss/search?q=dólar+câmbio+economia&hl=pt-BR&gl=BR&ceid=BR:pt-419",
            timeout=8,
        )
        root = ET.fromstring(r.content)
        items = root.findall(".//item")
        results = []
        for item in items[:10]:
            title = item.findtext("title") or ""
            link  = item.findtext("link") or ""
            pub   = item.findtext("pubDate") or ""
            results.append(
                {"title": title, "description": "", "url": link,
                 "source": "Google News", "published": pub[:16]}
            )
        return results
    except Exception as exc:
        log.warning("RSS fallback falhou: %s", exc)

    # Último recurso: dados de exemplo
    return [
        {
            "title": "Dólar oscila com dados do mercado americano",
            "description": "Investidores aguardam dados de inflação nos EUA.",
            "url": "#", "source": "Demo", "published": "2024-01-01",
        },
        {
            "title": "Banco Central mantém taxa Selic",
            "description": "Decisão impacta câmbio e expectativas de mercado.",
            "url": "#", "source": "Demo", "published": "2024-01-01",
        },
    ]


def aggregate_sentiment(articles: List[Dict]) -> float:
    """Média ponderada de sentimento das notícias."""
    if not articles:
        return 0.0
    scores = [a.get("sentiment", 0.0) for a in articles]
    return round(sum(scores) / len(scores), 2)
