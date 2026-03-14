"""
Gemini API 동작 테스트.

실행 방법 (프로젝트 루트에서):
  python test_gemini_api.py

사용 모델: GEMINI_MODEL 환경 변수 또는 기본값 gemini-2.5-flash
"""
from pathlib import Path
import os
from dotenv import load_dotenv

# .env 로드
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)

# 테스트용 모델 (목록 조회로 사용 가능한 모델 사용)
os.environ["GEMINI_MODEL"] = "gemini-2.5-flash"

from app.services.summary_service import summarize_news_items, FALLBACK_AI_SUMMARY

# 테스트용 기사 1건 (실제 API 호출 1회만 수행)
TEST_ARTICLE = {
    "title": "API 테스트용 더미 기사",
    "link": "https://example.com/test",
    "published": "2026-03-14",
    "summary": "이것은 Gemini API 연결 테스트를 위한 짧은 텍스트입니다.",
}

def main():
    print("모델: gemini-2.5-flash")
    print("API 호출 중...")
    result = summarize_news_items([TEST_ARTICLE])
    if not result:
        print("FAIL: 결과가 비어 있음")
        return 1
    item = result[0]
    ai_summary = (item.get("ai_summary") or "").strip()
    if ai_summary == FALLBACK_AI_SUMMARY or not ai_summary:
        print("FAIL: 요약이 생성되지 않음 (API 키 또는 API 오류 가능)")
        return 1
    print("OK: API 정상 동작")
    print("  ai_summary:", ai_summary[:80] + "..." if len(ai_summary) > 80 else ai_summary)
    return 0

if __name__ == "__main__":
    exit(main())
