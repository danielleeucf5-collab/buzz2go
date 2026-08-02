from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from src.fetch_trends import fetch_trending_topics
from src.gemini_writer import write_article
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
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


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

            sources = [{
                "name": "Google Trends via SerpAPI",
                "url": "https://trends.google.com/",
            }]
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
                posts.append(article)

        if topics:
            save_posts(posts)

    site_url = os.getenv("SITE_URL", "https://buzz2go.pages.dev")
    build_site(posts, PUBLIC_DIR, site_url)
    print(f"완료: {len(posts)}개 기사, 출력 폴더={PUBLIC_DIR}")


if __name__ == "__main__":
    main()
