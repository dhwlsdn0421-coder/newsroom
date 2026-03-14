# Progress

## 완료 이력
- 2025-03-14 · 프로젝트 초기화: AGENTS.md, .cursor/rules, memory_bank 6종, .cursor/plans 생성 (가이드 기준)
- 2025-03-14 · Phase 1 구현: main.py (YouTube Info Viewer) — URL 입력/조회, yt-dlp 연동, 썸네일·제목·조회수 표시, URL 유효성·예외 처리
- 2025-03-14 · 다운로드 버튼 추가: 기본 저장 위치 Downloads, QThread·진행 상태 표시
- 2025-03-14 · 고화질 다운로드: bestvideo+bestaudio/best, merge mp4, 진행 메시지(다운로드 중 % / 병합 중 / 완료)
- 2025-03-14 · Qt 플랫폼 플러그인 경로 설정 (Windows "no Qt platform plugin" 대응)
- 2025-03-14 · Git 리포지토리 초기화, .gitignore 추가
- 2025-03-14 · memory_bank 전반 업데이트 및 푸시 준비
- 2025-03-14 · **FastAPI 뉴스룸 백엔드 MVP 완성**: GET /health, POST /summarize, RSS 수집(rss_fetcher·feedparser), Gemini 요약(summary_service·GEMINI_API_KEY), news 라우터, .env/.env.sample, load_dotenv(프로젝트 루트 기준), GitHub 리포지토리 newsroom 생성 및 origin 설정
- 2025-03-14 · **Streamlit 리팩토링 완성**: FastAPI 엔드포인트 제거, streamlit_app.py 단일 앱(나만의 뉴스룸), rss_fetcher·summary_service 재사용, .env/st.secrets 이중 지원(로컬·배포), .streamlit/config.toml·secrets.toml(예시)·배포 준비, 기본 모델 gemini-2.5-flash, test_gemini_api.py·list_gemini_models.py 터미널 테스트 스크립트
