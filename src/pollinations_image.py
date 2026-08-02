from __future__ import annotations

import hashlib
import os
from pathlib import Path

import requests


POLLINATIONS_IMAGE_URL = "https://gen.pollinations.ai/v1/images/generations"


def generate_article_image(article: dict, public_dir: Path) -> dict[str, str] | None:
    """기사용 16:9 AI 일러스트를 생성하고 public/images에 저장합니다."""
    api_key = os.getenv("POLLINATIONS_API_KEY", "").strip()
    if not api_key:
        print("[Pollinations] API 키가 없어 이미지 생성을 건너뜁니다.")
        return None

    model = os.getenv("POLLINATIONS_IMAGE_MODEL", "nanobanana").strip()
    title = str(article.get("title", "")).strip()
    summary = str(article.get("summary", "")).strip()
    slug = str(article.get("slug", "article")).strip() or "article"
    prompt = (
        "Professional 16:9 editorial illustration for a Korean news blog. "
        f"Topic: {title}. Context: {summary}. "
        "Clean modern composition, informative and neutral tone, realistic lighting, "
        "no text, no letters, no logos, no watermarks, no recognizable real people, "
        "do not imitate a documentary photograph of an actual event."
    )
    seed = int(hashlib.sha256(slug.encode("utf-8")).hexdigest()[:8], 16)

    try:
        response = requests.post(
            POLLINATIONS_IMAGE_URL,
            json={
                "prompt": prompt,
                "model": model,
                "size": "1200x675",
                "quality": "medium",
                "response_format": "url",
                "safe": True,
                "user": f"buzz2go-{seed}",
            },
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=180,
        )
        response.raise_for_status()
        payload = response.json()
        image_url = payload.get("data", [{}])[0].get("url", "")
        if not image_url:
            raise RuntimeError("응답에 이미지 URL이 없습니다.")

        image_response = requests.get(image_url, timeout=60)
        image_response.raise_for_status()
        content_type = image_response.headers.get("content-type", "").lower()
        if not content_type.startswith("image/"):
            raise RuntimeError(f"이미지가 아닌 응답을 받았습니다: {content_type}")

        extension = {
            "image/png": "png",
            "image/webp": "webp",
        }.get(content_type.split(";")[0], "jpg")

        images_dir = public_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        image_path = images_dir / f"{slug}.{extension}"
        image_path.write_bytes(image_response.content)
        return {
            "image_url": f"/images/{slug}.{extension}",
            "image_alt": f"{title} 기사 대표 AI 일러스트",
            "image_credit": "AI-generated with Pollinations.ai",
        }
    except Exception as exc:
        print(f"[Pollinations] 이미지 생성 실패: {type(exc).__name__}: {exc}")
        return None
