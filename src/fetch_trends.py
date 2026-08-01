from __future__ import annotations

import os
from typing import Any

import requests


SERPAPI_URL = "https://serpapi.com/search.json"


def fetch_trending_topics(limit: int = 5) -> list[dict[str, Any]]:
    api_key = os.getenv("SERPAPI_KEY", "").strip()
    if not api_key:
        return []

    params = {
        "engine": "google_trends_trending_now",
        "api_key": api_key,
        "geo": os.getenv("TREND_GEO", "TW"),
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
