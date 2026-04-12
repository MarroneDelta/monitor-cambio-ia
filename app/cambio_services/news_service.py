"""
services/news_service.py — Notícias e Sentimento (Versão 2.0 - Cache Reset)
"""

import logging
from typing import List, Dict, Optional
import streamlit as st
import requests
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET
from email.utils import parsedate_to_datetime
from config import NEWS_API_KEY

log = logging.getLogger(__name__)

_POSITIVE_WORDS = {"alta", "subiu", "cresceu", "valoriz", "ganho", "lucro", "positiv", "recupera", "recorde"}
_NEGATIVE_WORDS = {"queda", "caiu", "baixou", "desvaloriza", "perda", "risco", "negativ", "crise", "inflação"}

def _simple_sentiment(text: str) -> float:
    text_lower = text.lower()
    pos = sum(1 for w in _POSITIVE_WORDS if w in text_lower)
    neg = sum(1 for w in _NEGATIVE_WORDS if w in text_lower)
    total = pos + neg
    return round((pos - neg) / total, 2) if total > 0 else 0.0

@st.cache_data(ttl=1200, show_spinner=False)
def get_latest_market_news(query: str = "economia Brasil mercado financeiro") -> List[Dict]:
    """Busca notícias recentes, combinando NewsAPI e RSS, com filtro rigoroso de data."""
    api_results = _fetch_newsapi(query) or []
    rss_results = _fetch_rss_fallback(query) or []
    
    combined = api_results + rss_results
    final_list = []
    seen = set()
    
    # Janela de 10 dias para garantir volume de Abril
    limit = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')

    for art in combined:
        title = art.get("title", "").strip()
        pub = art.get("published", "")[:10]
        if title and title.lower() not in seen and pub >= limit:
            seen.add(title.lower())
            art["sentiment"] = _simple_sentiment(title + " " + art.get("description", ""))
            final_list.append(art)
            
    # Ordena: Mais novas primeiro
    final_list.sort(key=lambda x: x.get("published", ""), reverse=True)
    return final_list[:20]

def _fetch_newsapi(query: str) -> List[Dict]:
    if not NEWS_API_KEY: return []
    try:
        # Tenta Top Headlines primeiro
        r = requests.get("https://newsapi.org/v2/top-headlines", params={
            "category": "business", "country": "br", "pageSize": 30, "apiKey": NEWS_API_KEY
        }, timeout=8)
        articles = r.json().get("articles", []) if r.status_code == 200 else []
        
        # Tenta Everything se for pouco
        if len(articles) < 10:
            r = requests.get("https://newsapi.org/v2/everything", params={
                "q": query, "language": "pt", "sortBy": "publishedAt", "pageSize": 40, "apiKey": NEWS_API_KEY
            }, timeout=8)
            if r.status_code == 200:
                articles.extend(r.json().get("articles", []))
                
        return [{
            "title": a.get("title", ""), "description": a.get("description", ""),
            "url": a.get("url", ""), "source": a.get("source", {}).get("name", ""),
            "published": a.get("publishedAt", "")[:10]
        } for a in articles if a.get("title")]
    except: return []

def _fetch_rss_fallback(query: str) -> List[Dict]:
    try:
        q_rss = query.replace(" ", "+")
        url = f"https://news.google.com/rss/search?q={q_rss}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
        r = requests.get(url, timeout=8)
        root = ET.fromstring(r.content)
        items = root.findall(".//item")
        results = []
        for item in items[:20]:
            try:
                dt = parsedate_to_datetime(item.findtext("pubDate"))
                pub = dt.strftime('%Y-%m-%d')
            except: pub = datetime.now().strftime('%Y-%m-%d')
            results.append({
                "title": item.findtext("title") or "", "description": "",
                "url": item.findtext("link") or "", "source": "Google News", "published": pub
            })
        return results
    except: return []

def aggregate_sentiment(articles: List[Dict]) -> float:
    if not articles: return 0.0
    scores = [a.get("sentiment", 0.0) for a in articles]
    return round(sum(scores) / len(scores), 2)
