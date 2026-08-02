from __future__ import annotations

import os
from typing import Any

import requests
from bs4 import BeautifulSoup


SERPAPI_URL = "https://serpapi.com/search.json"
ARTICLE_TIMEOUT = 15
MAX_ARTICLE_CHARS = 6000


def fetch_trending_topics(limit: int = 5) -> list[dict[str, Any]]:
    api_key = os.getenv("SERPAPI_KEY", "").strip()
    if not api_key:
        return []

    params = {
        "engine": "google_trends_trending_now",
        "api_key": api_key,
        "geo": os.getenv("TREND_GEO", "KR"),
        "hl": os.getenv("TREND_LANGUAGE", "ko"),
    }

    response = requests.get(SERPAPI_URL, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()

    candidates = (
        payload.get("trending_searches")
        or payload.get("daily_searches")
        or payload.get("trends")
        or []
    )

    topics: list[dict[str, Any]] = []
    for item in candidates:
        query = item.get("query") or item.get("title") or item.get("search_term")
        if not query:
            continue
        topics.append({
            "query": str(query),
            "traffic": item.get("search_volume") or item.get("traffic"),
            "raw": item,
        })
        if len(topics) >= limit:
            break

    return topics


def _extract_article_text(url: str) -> str:
    """기사 URL에서 모델에 전달할 본문 텍스트를 추출합니다."""
    response = requests.get(
        url,
        timeout=ARTICLE_TIMEOUT,
        headers={"User-Agent": "Buzz2Go/1.0 (+news research bot)"},
    )
    response.raise_for_status()
    content_type = response.headers.get("content-type", "").lower()
    if "html" not in content_type:
        return ""

    soup = BeautifulSoup(response.text, "html.parser")
    for element in soup(["script", "style", "nav", "footer", "aside", "form"]):
        element.decompose()

    article = soup.find("article") or soup.find("main") or soup.body
    if article is None:
        return ""
    paragraphs = [
        element.get_text(" ", strip=True)
        for element in article.find_all(["p", "h1", "h2"])
    ]
    text = "\n".join(paragraph for paragraph in paragraphs if len(paragraph) >= 30)
    return text[:MAX_ARTICLE_CHARS]


def fetch_news_sources(query: str, limit: int = 6) -> list[dict[str, str]]:
    """SerpAPI Google News 결과의 원문을 읽어 검증 가능한 출처로 반환합니다."""
    api_key = os.getenv("SERPAPI_KEY", "").strip()
    if not api_key or not query.strip():
        return []

    params = {
        "engine": "google_news",
        "api_key": api_key,
        "q": query.strip(),
        "gl": os.getenv("TREND_GEO", "KR").lower(),
        "hl": os.getenv("TREND_LANGUAGE", "ko").lower(),
    }
    response = requests.get(SERPAPI_URL, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        raise RuntimeError(f"SerpAPI 뉴스 검색 실패: {payload['error']}")

    sources: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for item in payload.get("news_results", []):
        url = str(item.get("link", "")).strip()
        if not url or url in seen_urls:
            continue
        try:
            excerpt = _extract_article_text(url)
        except requests.RequestException:
            continue
        if len(excerpt) < 200:
            continue

        source = item.get("source") or {}
        if isinstance(source, dict):
            source_name = source.get("name") or source.get("title")
        else:
            source_name = source
        sources.append({
            "name": str(source_name or "출처").strip(),
            "title": str(item.get("title", "")).strip(),
            "published_at": str(item.get("iso_date") or item.get("date") or "").strip(),
            "url": url,
            "excerpt": excerpt,
        })
        seen_urls.add(url)
        if len(sources) >= limit:
            break

    return sources
