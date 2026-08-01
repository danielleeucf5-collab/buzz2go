# Buzz2Go Starter Kit

Cloudflare Pages + GitHub + Python으로 운영하는 정적 AI 트렌드 뉴스 사이트입니다.

## 핵심 구조

1. SerpAPI에서 Trending Now 데이터를 가져옵니다.
2. Gemini가 원문 복사가 아닌 독자적인 요약 기사 초안을 만듭니다.
3. Python이 `public/` 아래에 홈페이지와 기사 HTML을 생성합니다.
4. GitHub에 push하면 Cloudflare Pages가 자동 배포합니다.

## 1. 가장 빠른 테스트

Windows PowerShell:

```powershell
cd C:\Buzz2Go
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run_pipeline.py --sample
```

생성된 `public/index.html`을 브라우저로 열어 확인합니다.

## 2. API 키 설정

`.env.example`을 복사해 `.env`로 바꿉니다.

```env
SERPAPI_KEY=...
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash
TREND_GEO=TW
SITE_URL=https://buzz2go.pages.dev
```

API 키는 절대 GitHub에 올리지 마세요. `.env`는 `.gitignore`에 포함되어 있습니다.

## 3. 실제 자동 생성

```powershell
python run_pipeline.py
```

키가 없거나 API 호출이 실패하면 프로그램은 기존 데이터와 샘플 데이터로 사이트를 생성합니다.

## 4. GitHub에 업로드

```powershell
git init
git add .
git commit -m "Initial Buzz2Go starter"
git branch -M main
git remote add origin https://github.com/danielleeucf5-collab/buzz2go.git
git push -u origin main
```

## 5. Cloudflare Pages 설정

- Framework preset: `None`
- Build command: 비워 둠
- Build output directory: `public`

GitHub 저장소가 비어 있으면 Cloudflare가 clone 단계에서 실패할 수 있으므로 먼저 첫 commit을 push하세요.

## 6. GitHub Actions 자동 실행

저장소에서 다음 Secrets를 등록합니다.

- `SERPAPI_KEY`
- `GEMINI_API_KEY`

경로:

`Settings → Secrets and variables → Actions → New repository secret`

기본 워크플로는 대만 시간 오전 7시 15분에 실행되도록 설정되어 있습니다. GitHub Actions cron은 UTC 기준입니다.

## 7. 기사 품질 원칙

- 원문을 그대로 복사하지 않습니다.
- 최소 2개 이상의 출처를 확인하도록 설계합니다.
- 출처 링크를 기사 하단에 표시합니다.
- 의료·법률·투자·정치·사건사고는 자동 공개보다 검토 후 공개가 안전합니다.
- 제목만 과장하는 클릭 유도형 문구를 피합니다.

## 주요 파일

- `run_pipeline.py`: 전체 자동화 실행
- `src/fetch_trends.py`: SerpAPI Trending Now 수집
- `src/gemini_writer.py`: Gemini 기사 생성
- `src/site_builder.py`: HTML, sitemap, RSS 생성
- `data/posts.json`: 기사 데이터
- `public/`: Cloudflare Pages 공개 폴더
