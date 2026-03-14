"""
FastAPI 앱 진입점 (My Newsroom API)

실행 방법 (프로젝트 루트에서):
  uvicorn app.main:app --reload

  → http://127.0.0.1:8000 에서 서버 실행
  → http://127.0.0.1:8000/docs 에서 Swagger UI 확인
  → .env 파일이 있으면 자동으로 로드 (GEMINI_API_KEY 등)
"""

from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트의 .env 로드 (실행 경로와 무관하게 동작)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

from fastapi import FastAPI

from app.routers import news

# ----- 1. FastAPI 앱 인스턴스 생성 -----
# FastAPI(...) 에 제목, 설명 등을 넣으면 /docs 화면에 반영됩니다.
app = FastAPI(
    title="My Newsroom API",
    description="RSS 피드를 수집하고 AI로 요약하는 뉴스룸 API (교육용)",
    version="1.0.0",
)

# ----- 2. 라우터 등록 -----
# include_router() 로 각 라우터(경로 묶음)를 앱에 붙입니다.
# news.router 에는 GET /health, POST /summarize 가 정의되어 있습니다.
app.include_router(news.router)
