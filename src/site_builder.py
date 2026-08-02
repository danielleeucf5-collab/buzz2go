from __future__ import annotations

import html
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import quote


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^0-9a-z가-힣]+", "-", value)
    return value.strip("-") or "article"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def format_date(value: str) -> str:
    try:
        return datetime.fromisoformat(value).strftime("%Y.%m.%d")
    except ValueError:
        return value[:10]


def header() -> str:
    return '''<header class="site-header">
  <div class="container header-row">
    <a class="brand" href="/">
      <span class="brand-mark">B2G</span>
      <span><h1>Buzz2Go</h1><p>Trending News, Powered by AI</p></span>
    </a>
    <nav><a href="/">홈</a><a href="/about.html">소개</a><a href="/feed.xml">RSS</a></nav>
  </div>
</header>'''


def footer(year: int) -> str:
    return f'''<footer>
  <div class="container footer-row">
    <strong>© {year} Buzz2Go</strong>
    <div class="notice">AI 보조로 작성된 콘텐츠는 공개 전 사실관계와 출처를 검토해야 합니다.</div>
  </div>
</footer>'''


def build_site(posts: list[dict], public_dir: Path, site_url: str) -> None:
    posts_dir = public_dir / "posts"
    posts_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now().astimezone()

    normalized: list[dict] = []
    for item in posts:
        post = dict(item)
        post["slug"] = post.get("slug") or slugify(post["title"])
        post.setdefault("category", "트렌드")
        post.setdefault("summary", "")
        post.setdefault("content", [])
        post.setdefault("sources", [])
        post.setdefault("published_at", now.isoformat(timespec="seconds"))
        normalized.append(post)

        source_items = "".join(
            f'<li><a href="{esc(src.get("url", "#"))}" target="_blank" rel="noopener noreferrer">'
            f'{esc(src.get("name", "출처"))} — {esc(src.get("title", "원문"))}</a>'
            f'{" (" + esc(src.get("published_at")) + ")" if src.get("published_at") else ""}</li>'
            for src in post["sources"]
        ) or "<li>등록된 출처가 없습니다. 공개 전 확인이 필요합니다.</li>"

        paragraphs = "".join(f"<p>{esc(p)}</p>" for p in post["content"])
        canonical = f"{site_url.rstrip('/')}/posts/{quote(post['slug'])}.html"

        article_html = f'''<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{esc(post["title"])} | Buzz2Go</title>
  <meta name="description" content="{esc(post["summary"])}">
  <link rel="canonical" href="{esc(canonical)}">
  <link rel="stylesheet" href="/assets/style.css">
</head>
<body>
{header()}
<main class="article-wrap container">
  <article class="article">
    <span class="badge">{esc(post["category"])}</span>
    <h1>{esc(post["title"])}</h1>
    <p class="lead">{esc(post["summary"])}</p>
    <div class="meta">{esc(format_date(post["published_at"]))}</div>
    <div class="article-body">{paragraphs}</div>
    <section class="sources"><h2>출처</h2><ul>{source_items}</ul></section>
  </article>
</main>
{footer(now.year)}
</body>
</html>'''
        (posts_dir / f'{post["slug"]}.html').write_text(article_html, encoding="utf-8")

    categories = ["전체"] + sorted({p["category"] for p in normalized})
    chips = "".join(
        f'<button class="chip{" active" if c == "전체" else ""}" data-category="{esc(c)}">{esc(c)}</button>'
        for c in categories
    )
    cards = "".join(
        f'''<article class="card" data-card="{esc(p["category"])}">
  <span class="badge">{esc(p["category"])}</span>
  <h3><a href="/posts/{esc(p["slug"])}.html">{esc(p["title"])}</a></h3>
  <p>{esc(p["summary"])}</p>
  <div class="meta">{esc(format_date(p["published_at"]))}</div>
</article>'''
        for p in sorted(normalized, key=lambda x: x["published_at"], reverse=True)
    )

    index_html = f'''<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Buzz2Go | Trending News, Powered by AI</title>
  <meta name="description" content="최신 검색 트렌드와 주요 이슈를 출처와 함께 빠르게 정리합니다.">
  <link rel="canonical" href="{esc(site_url.rstrip("/"))}/">
  <link rel="stylesheet" href="/assets/style.css">
</head>
<body>
{header()}
<main class="container">
  <section class="hero">
    <div class="kicker">Trending now</div>
    <h2>지금 사람들이 찾는 이슈를 더 분명하게.</h2>
    <p>검색량만 따라가지 않고 출처, 맥락, 실제 영향을 함께 확인합니다.</p>
    <div class="toolbar">{chips}</div>
  </section>
  <section class="news-grid">{cards or '<div class="empty">아직 등록된 기사가 없습니다.</div>'}</section>
</main>
{footer(now.year)}
<script src="/assets/app.js"></script>
</body>
</html>'''
    (public_dir / "index.html").write_text(index_html, encoding="utf-8")

    about_html = f'''<!doctype html><html lang="ko"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>소개 | Buzz2Go</title><link rel="stylesheet" href="/assets/style.css"></head>
<body>{header()}<main class="article-wrap container"><article class="article">
<span class="badge">About</span><h1>Buzz2Go 소개</h1>
<p class="lead">검색 트렌드를 발견하고 여러 출처를 확인해 핵심 맥락을 정리하는 독립 프로젝트입니다.</p>
<div class="article-body"><p>Buzz2Go는 AI를 편집 보조 도구로 사용하지만, AI가 생성한 문장을 사실 확인 없이 그대로 공개하는 것을 목표로 하지 않습니다.</p>
<p>의료, 법률, 투자, 정치, 사건·사고 등 민감한 주제는 자동 공개하지 않고 사람이 검토하는 운영 방식을 권장합니다.</p></div>
</article></main>{footer(now.year)}</body></html>'''
    (public_dir / "about.html").write_text(about_html, encoding="utf-8")

    urls = [f"{site_url.rstrip('/')}/"] + [
        f"{site_url.rstrip('/')}/posts/{quote(p['slug'])}.html" for p in normalized
    ]
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sitemap += "\n".join(f"  <url><loc>{esc(u)}</loc></url>" for u in urls)
    sitemap += "\n</urlset>\n"
    (public_dir / "sitemap.xml").write_text(sitemap, encoding="utf-8")

    (public_dir / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {site_url.rstrip('/')}/sitemap.xml\n",
        encoding="utf-8",
    )

    items = "".join(
        f"<item><title>{esc(p['title'])}</title>"
        f"<link>{site_url.rstrip('/')}/posts/{quote(p['slug'])}.html</link>"
        f"<description>{esc(p['summary'])}</description></item>"
        for p in normalized[:20]
    )
    feed = f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Buzz2Go</title>
<link>{esc(site_url)}</link><description>Trending News, Powered by AI</description>{items}</channel></rss>'''
    (public_dir / "feed.xml").write_text(feed, encoding="utf-8")

    (public_dir / "_headers").write_text(
        "/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n",
        encoding="utf-8",
    )

    data_dir = public_dir / "data"
    data_dir.mkdir(exist_ok=True)
    (data_dir / "posts.json").write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
