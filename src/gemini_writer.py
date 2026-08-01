from __future__ import annotations

import json
import os
from typing import Any

import requests


def write_article(topic: str, sources: list[dict[str, str]] | None = None) -> dict[str, Any] | None:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
    if not api_key:
        return None

    source_text = "\n".join(
        f"- {s.get('name', 'Source')}: {s.get('url', '')}"
        for s in (sources or [])
    ) or "- 출처 정보 없음: 게시 전 반드시 직접 확인"

    prompt = f'''
당신은 Buzz2Go의 편집자입니다.
주제: {topic}

출처:
{source_text}

다음 규칙을 지켜 한국어 JSON만 출력하세요.
- 원문 문장을 복사하지 말고 독자적으로 재구성
- 확인되지 않은 내용을 사실처럼 단정하지 않기
- 선정적 제목 금지
- title, category, summary, content 배열을 포함
- content는 3~5개 문단
- 출처가 부족하면 그 한계를 본문에 명시
출력 예:
{{"title":"...", "category":"트렌드", "summary":"...", "content":["문단1","문단2","문단3"]}}
'''.strip()

    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/{model}:generateContent"
    )
    response = requests.post(
        url,
        params={"key": api_key},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        },
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()

    text = payload["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)
