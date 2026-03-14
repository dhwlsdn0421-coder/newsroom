"""
뉴스룸 API 라우터.

- GET /health: 서버 상태 확인
- POST /summarize: RSS 수집 후 Gemini 요약 (fetch_rss_items -> summarize_news_items)
"""

from fastapi import APIRouter, HTTPException

from pydantic import BaseModel, Field

# 프로젝트 루트 기준 모듈 (실행 시 루트가 PYTHONPATH에 있어야 함)
from rss_fetcher import fetch_rss_items
from app.services.summary_service import summarize_news_items


# ----- 요청/응답 스키마 -----


class NewsroomRequest(BaseModel):
    """POST /summarize 요청 body."""

    feed_url: str = Field(..., description="RSS 피드 URL (http:// 또는 https://)")
    limit: int = Field(default=5, ge=1, le=100, description="수집·요약할 기사 개수 (1~100)")


class NewsItem(BaseModel):
    """요약이 포함된 뉴스 한 건."""

    title: str = Field(..., description="기사 제목")
    link: str = Field(..., description="기사 URL")
    published: str | None = Field(default=None, description="발행일 (ISO 8601 등)")
    summary: str | None = Field(default=None, description="원문 요약/본문 일부")
    ai_summary: str = Field(..., description="AI 요약")
    why_it_matters: str = Field(..., description="왜 중요한가")
    keywords: list[str] = Field(default_factory=list, description="키워드 목록")


class NewsroomResponse(BaseModel):
    """POST /summarize 응답 body."""

    items: list[NewsItem] = Field(default_factory=list, description="요약이 포함된 뉴스 목록")


# ----- 라우터 -----

router = APIRouter(tags=["news"])


@router.get("/health")
def health():
    """서버 상태 확인. GET /health"""
    return {"status": "ok"}


@router.post("/summarize", response_model=NewsroomResponse)
def summarize(request: NewsroomRequest) -> NewsroomResponse:
    """
    RSS 피드를 수집한 뒤 각 기사에 대해 AI 요약을 붙여 반환합니다.

    1. fetch_rss_items(feed_url, limit) 로 기사 목록 수집
    2. summarize_news_items(목록) 로 요약·키워드 추가
    """
    try:
        # 1) RSS 수집
        articles = fetch_rss_items(request.feed_url, request.limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"RSS 수집 실패: {e}") from e

    # 2) 요약 추가 (실패 시 fallback 메시지가 들어가므로 예외 없이 반환)
    summarized = summarize_news_items(articles)

    # 3) 응답 스키마로 변환 (필드 누락 시 기본값)
    items = [
        NewsItem(
            title=item.get("title") or "",
            link=item.get("link") or "",
            published=item.get("published"),
            summary=item.get("summary"),
            ai_summary=item.get("ai_summary") or "",
            why_it_matters=item.get("why_it_matters") or "",
            keywords=item.get("keywords") or [],
        )
        for item in summarized
    ]

    return NewsroomResponse(items=items)
