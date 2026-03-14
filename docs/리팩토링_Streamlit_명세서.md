# 리팩토링 검토 명세서: FastAPI → Streamlit 단일 앱

## 현재 상태

- **RSS 수집**: `rss_fetcher.py`의 `fetch_rss_items(feed_url, limit)` 사용
- **AI 요약**: `app/services/summary_service.py`의 `summarize_news_items(news_items)` 사용
- **FastAPI**: `app/main.py` + `app/routers/news.py`에서 GET /health, POST /summarize 제공

---

## 1. 리팩토링 계획

| 단계 | 내용 |
|------|------|
| 1 | Streamlit 의존성 추가 (`requirements.txt`에 `streamlit` 추가) |
| 2 | `streamlit_app.py` 신규 작성: RSS URL·기사 개수 입력 → 버튼 클릭 → 수집·요약 → 카드/섹션 표시, 친절한 에러 메시지 |
| 3 | 진입점 통일: 실행은 `streamlit run streamlit_app.py`만 사용 (uvicorn/FastAPI 실행 제거) |
| 4 | FastAPI 관련 코드 정리: 라우터·main 제거 또는 최소화 (선택 시 삭제) |
| 5 | `.env` / `GEMINI_API_KEY` 로드는 Streamlit 앱에서도 동일하게 적용 (프로젝트 루트 `.env`) |

**재사용 유지**

- `rss_fetcher.fetch_rss_items(feed_url, limit)` — 그대로 호출
- `app.services.summary_service.summarize_news_items(news_items)` — 그대로 호출  
- 두 모듈은 FastAPI와 무관한 순수 함수이므로 Streamlit에서 직접 import하여 사용

---

## 2. 삭제 또는 축소 가능한 FastAPI 관련 파일

| 파일 | 권장 조치 | 비고 |
|------|-----------|------|
| `app/main.py` | **삭제 가능** | Streamlit 단일 앱으로 전환 시 진입점 불필요 |
| `app/routers/news.py` | **삭제 가능** | 엔드포인트 호출 구조 제거 시 불필요 |
| `app/routers/__init__.py` | **삭제 가능** | 라우터 제거 시 함께 제거 |
| `app/__init__.py` | **유지** | `app.services.summary_service` import 경로 유지 |
| `app/services/summary_service.py` | **유지** | 최대한 재사용 |
| `app/services/__init__.py` | **유지** | 패키지 구조 유지 |
| `rss_fetcher.py` | **유지** | 루트에 두고 그대로 재사용 |

**선택 사항**

- FastAPI를 완전히 제거할 경우: `app/main.py`, `app/routers/` 전체 삭제. `requirements.txt`에서 `fastapi`, `uvicorn[standard]` 제거 가능.
- “나중에 API도 쓸 수 있게” 남겨둘 경우: `app/main.py`·`app/routers/` 유지하고, Streamlit은 별도 진입점(`streamlit_app.py`)만 추가.

---

## 3. 새 Streamlit 구조 제안

```
프로젝트 루트/
├── .env                    # GEMINI_API_KEY (기존 유지)
├── .env.sample             # (기존 유지)
├── streamlit_app.py        # ★ 새 진입점: Streamlit 단일 앱
├── rss_fetcher.py          # 재사용 (변경 없음)
├── app/
│   ├── __init__.py
│   └── services/
│       ├── __init__.py
│       └── summary_service.py   # 재사용 (변경 없음)
├── docs/
│   └── 리팩토링_Streamlit_명세서.md
└── requirements.txt       # streamlit 추가
```

**실행 방법**

```bash
# 프로젝트 루트에서
streamlit run streamlit_app.py
```

**화면 흐름 (단순·읽기 쉽게)**

1. 제목: "뉴스룸 – RSS 요약"
2. 입력: RSS 피드 URL (텍스트), 기사 개수 (숫자, 기본 5, 1~100)
3. 버튼: "뉴스 가져오기 & 요약"
4. 진행: `st.spinner`로 "RSS 수집 중…", "AI 요약 중…" 표시
5. 결과: 각 기사를 카드/섹션으로 표시 (제목, 링크, 발행일, AI 요약, 왜 중요한가, 키워드)
6. 에러: `ValueError` / `requests.RequestException` 등은 `st.error`로 초보자도 이해 가능한 한글 메시지로 출력

---

## 4. streamlit_app.py 초안

초안 코드는 프로젝트 루트의 `streamlit_app.py` 파일로 두었습니다. 요약:

- **환경 로드**: `pathlib` + `dotenv`로 프로젝트 루트 `.env` 로드 (기존과 동일)
- **재사용**: `rss_fetcher.fetch_rss_items`, `app.services.summary_service.summarize_news_items` 직접 호출
- **UI**: URL·개수 입력 → 버튼 → 스피너 → 카드 형태 결과, 에러 시 `st.error`로 안내

의존성: `requirements.txt`에 `streamlit` 추가 필요.
