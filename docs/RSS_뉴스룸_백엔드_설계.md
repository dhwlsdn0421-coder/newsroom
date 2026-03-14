# RSS 기반 IT 뉴스룸 백엔드 설계 (FastAPI)

> 사용자 RSS 주소 → 최신 뉴스 수집 → Gemini 요약 → JSON 반환.  
> 교육용으로 구조를 단순하게 유지한다.

---

## 1. 추천 폴더 구조

```
project-root/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 앱 생성, 라우터 등록, .env 로드
│   ├── routers/
│   │   ├── __init__.py
│   │   └── news.py          # 뉴스 관련 엔드포인트 (요청/응답 스키마 포함)
│   └── services/
│       ├── __init__.py
│       └── summary_service.py   # Gemini 요약 로직
├── rss_fetcher.py           # RSS 수집 (독립 모듈, app 외부)
├── .env                     # GEMINI_API_KEY (git 제외)
├── .env.sample
├── requirements.txt
└── docs/
    ├── RSS_수집_명세서.md
    └── RSS_뉴스룸_백엔드_설계.md  # 본 문서
```

**설계 원칙**

- **routers**: HTTP 요청/응답, 검증, 스키마만 담당. 비즈니스 로직은 services/ 또는 별도 모듈에 위임.
- **services**: 외부 API(Gemini) 호출, 데이터 가공. HTTP/라우팅은 모름.
- **rss_fetcher**: RSS 수집은 재사용 가능하므로 루트에 두고, app은 `from rss_fetcher import fetch_rss_items` 로 사용.
- **복잡도**: DTO는 라우터 파일에 두어, 초보자가 “엔드포인트 ↔ 스키마”를 한 파일에서 보도록 한다. 필요해지면 나중에 `app/schemas/` 로 분리 가능.

---

## 2. 필요한 패키지 목록

| 패키지 | 용도 |
|--------|------|
| **fastapi** | API 프레임워크 |
| **uvicorn[standard]** | ASGI 서버 (실행·개발) |
| **pydantic** | 요청/응답 스키마 (FastAPI에 포함) |
| **feedparser** | RSS/Atom 파싱 |
| **requests** | RSS URL HTTP 요청 (타임아웃·스트리밍) |
| **google-genai** | Gemini API 클라이언트 |
| **python-dotenv** | .env에서 GEMINI_API_KEY 로드 |

**requirements.txt 예시**

```text
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
feedparser>=6.0.0,<7.0.0
requests>=2.28
google-genai>=1.0.0
python-dotenv>=1.0.0
```

(기존 프로젝트에 PyQt5, yt-dlp 등이 있으면 그대로 두고 위 패키지만 추가해도 됨.)

---

## 3. 파일별 책임

| 파일 | 책임 |
|------|------|
| **app/main.py** | FastAPI 앱 생성, `load_dotenv()`, `include_router(news.router)`. 앱 제목·설명 등 메타. |
| **app/routers/news.py** | `GET /health`, `POST /summarize` 정의. `NewsroomRequest` / `NewsroomResponse` 등 Pydantic 모델. 라우터는 `fetch_rss_items` → `summarize_news_items` 호출만 하고, 예외 시 HTTP 상태 코드·메시지 반환. |
| **app/services/summary_service.py** | `summarize_news_items(news_items) -> list[dict]`. 환경변수 `GEMINI_API_KEY`, `GEMINI_MODEL` 읽기. Gemini 호출, JSON 파싱, 실패 시 fallback 메시지 반환. HTTP/라우팅 무관. |
| **rss_fetcher.py** | `fetch_rss_items(feed_url, limit)` → `list[dict]`. RSS URL 검증, requests로 수집, feedparser 파싱, 정렬·중복 제거·limit. 명세는 `docs/RSS_수집_명세서.md` 참고. |

**데이터 흐름**

1. 클라이언트 → `POST /summarize` (feed_url, limit)
2. **news.py** → `fetch_rss_items(feed_url, limit)` → 기사 리스트
3. **news.py** → `summarize_news_items(기사 리스트)` → ai_summary, why_it_matters, keywords 추가
4. **news.py** → Pydantic으로 JSON 응답 생성 후 반환

---

## 4. 구현 순서

교육용으로 “동작하는 것부터 보여주기”를 기준으로 한 순서다.

| 순서 | 작업 | 비고 |
|------|------|------|
| 1 | **가상환경 + requirements 설치** | `python -m venv .venv` → `pip install -r requirements.txt` |
| 2 | **rss_fetcher.py** | `fetch_rss_items` 구현 및 단위 테스트(선택). 명세서대로 입력 검증·반환 스키마 준수. |
| 3 | **.env.sample / .env** | `GEMINI_API_KEY`, (선택) `GEMINI_MODEL`. `python-dotenv`로 로드할 준비. |
| 4 | **app/services/summary_service.py** | `summarize_news_items` 구현. 환경변수에서 키 읽기, 실패 시 fallback. |
| 5 | **app/main.py** | `load_dotenv()`, FastAPI 앱 생성, 제목 등 설정. |
| 6 | **app/routers/news.py** | 스키마(NewsroomRequest, NewsroomResponse, NewsItem) 정의, `GET /health`, `POST /summarize` 구현. |
| 7 | **app/main.py에 라우터 등록** | `app.include_router(news.router)`. |
| 8 | **실행·검증** | `uvicorn app.main:app --reload` → /docs에서 POST /summarize 호출. |

이미 구현된 상태라면, “2 → 4 → 6 → 7”은 완료된 것으로 보고, 배포·문서화·테스트 추가 순으로 확장하면 된다.

---

## 5. 최소 MVP 기준 엔드포인트 설계

### 5.1 엔드포인트 목록

| 메서드 | 경로 | 설명 |
|--------|------|------|
| **GET** | `/health` | 서버 생존 확인. 응답: `{"status": "ok"}` |
| **POST** | `/summarize` | RSS 주소 + 개수 받아서, 수집 후 요약해 JSON 반환 |

MVP에서는 위 두 개만 있으면 된다. (추가: `/feeds` 목록, 인증 등은 이후 단계.)

### 5.2 POST /summarize

**요청 (Request Body)**

```json
{
  "feed_url": "https://www.wired.com/feed/rss",
  "limit": 5
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| feed_url | string | O | RSS 피드 URL (http:// 또는 https://) |
| limit | integer | X | 수집·요약할 기사 수. 기본 5, 1~100 권장. |

**응답 (200 OK)**

```json
{
  "items": [
    {
      "title": "기사 제목",
      "link": "https://...",
      "published": "2025-03-14T12:00:00Z",
      "summary": "원문 요약 또는 null",
      "ai_summary": "Gemini가 생성한 2~3문장 요약",
      "why_it_matters": "왜 중요한지 1~2문장",
      "keywords": ["키워드1", "키워드2"]
    }
  ]
}
```

**에러**

- **400** : feed_url 검증 실패 (빈 값, 비 http(s) 등). body에 `detail` 메시지.
- **502** : RSS 수집 실패 (네트워크, 파싱 오류). body에 `detail` 메시지.
- 요약 실패 시: 현재처럼 200으로 응답하되, 각 항목에 `ai_summary`/`why_it_matters`/`keywords` fallback 메시지 또는 빈 배열을 넣어 반환해도 됨 (MVP에서는 이 방식으로 단순화 가능).

### 5.3 GET /health

- **응답 (200)**: `{"status": "ok"}`
- 용도: 로드밸런서·모니터링·배포 후 동작 확인.

---

## 요약

- **폴더**: `app/` 아래 `routers/`, `services/` 분리, RSS 수집은 `rss_fetcher.py`로 두는 구조가 유지보수와 교육에 적당하다.
- **패키지**: FastAPI, Uvicorn, feedparser, requests, google-genai, python-dotenv로 MVP 구성 가능.
- **파일 책임**: main = 앱·env, routers = 엔드포인트·스키마, services = Gemini 요약, rss_fetcher = RSS 수집.
- **구현 순서**: 환경 → rss_fetcher → .env → summary_service → main → news 라우터 → 라우터 등록 → 실행 검증.
- **MVP 엔드포인트**: `GET /health`, `POST /summarize` (요청/응답 스키마는 위와 같이 두면 된다).

이 설계를 기준으로 현재 코드와 맞는지 점검하고, 필요하면 엔드포인트나 스키마만 소폭 수정하면 된다.
