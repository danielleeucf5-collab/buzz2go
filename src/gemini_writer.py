from __future__ import annotations

import json
import os
from typing import Any

from google import genai
from google.genai import types


ARTICLE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": "과장하지 않은 한국어 기사 제목",
        },
        "category": {
            "type": "string",
            "description": "기사 카테고리. 예: AI, 기술, 경제, 사회, 트렌드",
        },
        "summary": {
            "type": "string",
            "description": "기사 핵심을 1~2문장으로 요약",
        },
        "content": {
            "type": "array",
            "description": "도입, 핵심 내용, 영향, 주의점, 전망, 결론을 포함한 기사 본문",
            "items": {"type": "string"},
            "minItems": 6,
            "maxItems": 12,
        },
        "publish": {"type": "boolean"},
        "rejection_reason": {"type": "string"},
        "selected_trend": {"type": "string"},
        "selection_reason": {"type": "string"},
        "trend_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "score_breakdown": {
            "type": "object",
            "properties": {
                "search_growth": {"type": "integer", "minimum": 0, "maximum": 20},
                "source_reliability": {"type": "integer", "minimum": 0, "maximum": 25},
                "cross_verification": {"type": "integer", "minimum": 0, "maximum": 15},
                "user_social_impact": {"type": "integer", "minimum": 0, "maximum": 15},
                "industry_market_impact": {"type": "integer", "minimum": 0, "maximum": 15},
                "sustainability": {"type": "integer", "minimum": 0, "maximum": 10},
            },
            "required": [
                "search_growth", "source_reliability", "cross_verification",
                "user_social_impact", "industry_market_impact", "sustainability",
            ],
            "additionalProperties": False,
        },
        "keywords": {
            "type": "array", "items": {"type": "string"},
            "minItems": 5, "maxItems": 10,
        },
        "hashtags": {
            "type": "array", "items": {"type": "string"},
            "minItems": 8, "maxItems": 12,
        },
        "sources": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "title": {"type": "string"},
                    "published_at": {"type": "string"},
                    "url": {"type": "string"},
                },
                "required": ["name", "title", "published_at", "url"],
                "additionalProperties": False,
            },
            "minItems": 3,
        },
    },
    "required": [
        "title", "category", "summary", "content", "publish",
        "rejection_reason", "selected_trend", "selection_reason",
        "trend_score", "score_breakdown", "keywords", "hashtags", "sources",
    ],
    "additionalProperties": False,
}


def _build_source_text(
    sources: list[dict[str, str]] | None,
) -> str:
    """출처 목록을 프롬프트에 넣을 텍스트로 변환합니다."""
    if not sources:
        return "- 제공된 출처 없음: 사실관계 확인이 제한적임을 본문에 명시"

    lines: list[str] = []
    for source in sources:
        name = str(source.get("name", "Source")).strip() or "Source"
        url = str(source.get("url", "")).strip()
        lines.append(f"- {name}: {url}")

    return "\n".join(lines)


def _validate_article(data: Any) -> dict[str, Any]:
    """Gemini 응답이 Buzz2Go에서 사용할 수 있는 형태인지 확인합니다."""
    if not isinstance(data, dict):
        raise ValueError("Gemini 응답의 최상위 값이 객체가 아닙니다.")

    required = tuple(ARTICLE_SCHEMA["required"])
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError(
            f"Gemini 응답에 필수 항목이 없습니다: {', '.join(missing)}"
        )

    if not data["publish"]:
        reason = str(data.get("rejection_reason", "선정 기준 미달")).strip()
        print(f"[Gemini] 기사 제외: {reason}")
        return {}

    title = str(data["title"]).strip()
    category = str(data["category"]).strip()
    summary = str(data["summary"]).strip()
    content_raw = data["content"]

    if not title:
        raise ValueError("기사 제목이 비어 있습니다.")
    if not category:
        category = "트렌드"
    if not summary:
        raise ValueError("기사 요약이 비어 있습니다.")
    if not isinstance(content_raw, list):
        raise ValueError("content는 문자열 배열이어야 합니다.")

    content = [
        str(paragraph).strip()
        for paragraph in content_raw
        if str(paragraph).strip()
    ]

    if len(content) < 6:
        raise ValueError("기사 본문은 최소 6개 문단이어야 합니다.")
    if len("".join(content)) < 1000:
        raise ValueError("기사 본문은 공백 제외 1,000자 이상이어야 합니다.")

    sources = data["sources"]
    if not isinstance(sources, list) or len(sources) < 3:
        raise ValueError("참고 자료는 3개 이상이어야 합니다.")
    independent_names = {
        str(source.get("name", "")).strip()
        for source in sources if isinstance(source, dict)
    }
    if len(independent_names - {""}) < 2:
        raise ValueError("서로 독립적인 출처가 2개 이상이어야 합니다.")

    score = int(data["trend_score"])
    breakdown_total = sum(int(value) for value in data["score_breakdown"].values())
    if breakdown_total != score:
        raise ValueError("트렌드 총점과 항목별 점수의 합계가 일치하지 않습니다.")
    if score < 70:
        print(f"[Gemini] 기사 제외: 트렌드 평가 {score}점")
        return {}

    return {
        "title": title,
        "category": category,
        "summary": summary,
        "content": content[:12],
        "selected_trend": str(data["selected_trend"]).strip(),
        "selection_reason": str(data["selection_reason"]).strip(),
        "trend_score": score,
        "score_breakdown": data["score_breakdown"],
        "keywords": [str(value).strip() for value in data["keywords"] if str(value).strip()],
        "hashtags": [str(value).strip() for value in data["hashtags"] if str(value).strip()],
        "sources": sources,
    }


def write_article(
    topic: str,
    sources: list[dict[str, str]] | None = None,
) -> dict[str, Any] | None:
    """
    Gemini API로 Buzz2Go 기사 초안을 생성합니다.

    필요한 환경변수:
      GEMINI_API_KEY
      GEMINI_API_KEY_2 (선택, 첫 번째 키 할당량 소진 시 사용)
      GEMINI_TEXT_MODEL 또는 GEMINI_MODEL

    반환값:
      {
        "title": str,
        "category": str,
        "summary": str,
        "content": list[str],
        "selected_trend": str,
        "selection_reason": str,
        "trend_score": int,
        "score_breakdown": dict[str, int],
        "keywords": list[str],
        "hashtags": list[str],
        "sources": list[dict],
      }

    API 키가 없으면 None을 반환합니다.
    그 외 API/응답 오류는 RuntimeError로 전달합니다.
    """
    api_keys = list(dict.fromkeys(
        key
        for key in (
            os.getenv("GEMINI_API_KEY", "").strip(),
            os.getenv("GEMINI_API_KEY_2", "").strip(),
        )
        if key
    ))
    model = (
        os.getenv("GEMINI_TEXT_MODEL")
        or os.getenv("GEMINI_MODEL")
        or "gemini-3.6-flash"
    ).strip()

    if not api_keys:
        print("[Gemini] API 키가 없어 기사 생성을 건너뜁니다.")
        return None

    topic = topic.strip()
    if not topic:
        raise ValueError("기사 주제가 비어 있습니다.")

    source_text = _build_source_text(sources)

    prompt = f"""
당신은 데이터 기반의 전문 뉴스 큐레이터이자 한국어 블로그 기자입니다.

[주제]
{topic}

[확인 가능한 출처]
{source_text}

[조사와 선정]
1. Google Search로 현재 시점의 최근 4시간 또는 오늘 자료를 직접 확인합니다.
2. 검색 증가도 20점, 출처 신뢰도 25점, 교차 검증 15점, 사용자·사회 영향 15점,
   산업·시장 영향 15점, 지속 가능성 10점으로 평가합니다.
3. 총점이 70점 미만이거나 독립적인 신뢰 출처가 2개 미만이면 publish=false로 응답합니다.
4. 루머, 정치적 선동, 확인되지 않은 사건·사고, 사생활 침해, 자극적인 연예 뉴스,
   광고성 콘텐츠는 제외합니다.

[사실 확인]
1. 실제 발생일과 자료 발행일, 최초 발표 주체, 핵심 수치와 인용을 원문에서 확인합니다.
2. 공식 발표를 우선하고 서로 다른 출처의 내용이 일치하는지 확인합니다.
3. 확정 사실과 검토·예정·미확정 내용을 명확히 구분합니다.
4. 검색 결과의 제목이나 요약문만으로 사실을 작성하지 않습니다.

[기사 작성]
1. 제목은 과장 없이 핵심 변화를 담아 35~55자 내외로 작성합니다.
2. 본문은 공백 제외 최소 1,000자, 권장 1,500~2,000자로 작성합니다.
3. content 문단 배열에 도입부, 확인된 핵심 내용, 사용자·산업·한국 시장 영향,
   주의할 점, 전망, 결론을 순서대로 담습니다.
4. 검색량 증가와 실제 뉴스 가치를 구분하고 단기 영향과 중장기 영향을 나눕니다.
5. 짧은 문단과 쉬운 한국어를 사용하며 번역투, 반복, 홍보성·감정적 표현을 피합니다.
6. 출처에 없는 사실·수치를 만들지 말고 근거 없는 전망을 하지 않습니다.
7. sources에는 실제로 원문을 확인한 자료를 3개 이상 기록하며 공식 자료를 우선합니다.
8. summary는 핵심을 1~2문장으로 정리하고 출력은 지정된 JSON 스키마만 따릅니다.
""".strip()

    response = None
    for key_index, api_key in enumerate(api_keys, start=1):
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.35,
                    max_output_tokens=8192,
                    response_mime_type="application/json",
                    response_json_schema=ARTICLE_SCHEMA,
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                ),
            )
            break
        except Exception as exc:
            status_code = getattr(exc, "status_code", None)
            is_quota_error = status_code == 429 or "RESOURCE_EXHAUSTED" in str(exc)
            has_next_key = key_index < len(api_keys)
            if is_quota_error and has_next_key:
                print(
                    f"[Gemini] API 키 {key_index}의 할당량이 소진되어 "
                    f"API 키 {key_index + 1}로 재시도합니다."
                )
                continue
            raise RuntimeError(
                f"Gemini 기사 생성 실패 "
                f"(model={model}, key={key_index}, error={type(exc).__name__}): {exc}"
            ) from exc

    if response is None:
        raise RuntimeError("사용 가능한 Gemini API 키가 없습니다.")

    try:
        response_text = (response.text or "").strip()
        if not response_text:
            raise RuntimeError("Gemini가 빈 응답을 반환했습니다.")

        parsed = json.loads(response_text)
        return _validate_article(parsed)

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Gemini 응답을 JSON으로 해석하지 못했습니다."
        ) from exc
    except Exception as exc:
        raise RuntimeError(
            f"Gemini 응답 처리 실패 "
            f"(model={model}, error={type(exc).__name__}): {exc}"
        ) from exc
