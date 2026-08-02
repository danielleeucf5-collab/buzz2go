from __future__ import annotations

import hashlib
import os
from pathlib import Path
from urllib.parse import quote

import requests


POLLINATIONS_IMAGE_URL = "https://gen.pollinations.ai/image"


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
        response = requests.get(
            f"{POLLINATIONS_IMAGE_URL}/{quote(prompt, safe='')}",
            params={
                "model": model,
                "width": 1200,
                "height": 675,
                "seed": seed,
                "safe": "true",
            },
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=180,
        )
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").lower()
        if not content_type.startswith("image/"):
            raise RuntimeError(f"이미지가 아닌 응답을 받았습니다: {content_type}")

        images_dir = public_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        image_path = images_dir / f"{slug}.jpg"
        image_path.write_bytes(response.content)
        return {
            "image_url": f"/images/{slug}.jpg",
            "image_alt": f"{title} 기사 대표 AI 일러스트",
            "image_credit": "AI-generated with Pollinations.ai",
        }
    except Exception as exc:
        print(f"[Pollinations] 이미지 생성 실패: {type(exc).__name__}: {exc}")
        return None
