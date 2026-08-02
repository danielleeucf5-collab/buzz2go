from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from src.fetch_trends import fetch_news_sources, fetch_trending_topics
from src.gemini_writer import write_article
from src.pollinations_image import generate_article_image
from src.site_builder import build_site, slugify


ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data" / "posts.json"
PUBLIC_DIR = ROOT / "public"


def configure_console() -> None:
    """Use UTF-8 for Korean status messages, especially on Windows."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")


def load_posts() -> list[dict]:
    if not DATA_FILE.exists():
        return []
    # utf-8-sig accepts both ordinary UTF-8 and files containing a BOM.
    return json.loads(DATA_FILE.read_text(encoding="utf-8-sig"))


def save_posts(posts: list[dict]) -> None:
    DATA_FILE.write_text(
        json.dumps(posts, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    configure_console()
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", action="store_true", help="API 호출 없이 사이트만 생성")
    args = parser.parse_args()

    load_dotenv()
    posts = load_posts()

    if not args.sample:
        limit = int(os.getenv("MAX_TOPICS", "5"))
        try:
            topics = fetch_trending_topics(limit=limit)
        except Exception as exc:
            print(
                f"[SerpAPI] 트렌드 수집 실패: {type(exc).__name__}: {exc}",
                file=sys.stderr,
            )
            topics = []

        existing_titles = {p.get("title", "") for p in posts}
        candidates: list[dict] = []
        for topic in topics:
            query = topic["query"]
            if query in existing_titles:
                continue

            try:
                sources = fetch_news_sources(query)
            except Exception as exc:
                print(
                    f"[SerpAPI] '{query}' 관련 뉴스 수집 실패: "
                    f"{type(exc).__name__}: {exc}",
                    file=sys.stderr,
                )
                continue
            independent_names = {source["name"] for source in sources}
            if len(sources) < 3 or len(independent_names) < 2:
                print(f"[SerpAPI] '{query}' 기사 제외: 검증 가능한 출처 부족")
                continue
            try:
                article = write_article(query, sources=sources)
            except Exception as exc:
                print(
                    f"[Gemini] '{query}' 기사 생성 실패: "
                    f"{type(exc).__name__}: {exc}",
                    file=sys.stderr,
                )
                continue
            if not article:
                continue

            candidates.append(article)

        if candidates:
            article = max(candidates, key=lambda item: item.get("trend_score", 0))
            if article["title"] not in existing_titles:
                article["slug"] = slugify(article["title"])
                article["published_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
                article.setdefault("sources", sources)
                image_data = generate_article_image(article, PUBLIC_DIR)
                if image_data:
                    article.update(image_data)
                posts.append(article)

        if topics:
            save_posts(posts)

    site_url = os.getenv("SITE_URL", "https://buzz2go.danielleeucf5.workers.dev")
    build_site(posts, PUBLIC_DIR, site_url)
    print(f"완료: {len(posts)}개 기사, 출력 폴더={PUBLIC_DIR}")


if __name__ == "__main__":
    main()
