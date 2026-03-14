"""
Gemini를 사용한 뉴스 요약 서비스.

- GEMINI_API_KEY 환경 변수로 API 키 로드
- 기본: gemini-2.0-flash (GEMINI_MODEL로 다른 모델 지정 가능)
"""

import json
import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

# 환경 변수 이름
ENV_API_KEY = "GEMINI_API_KEY"
ENV_MODEL = "GEMINI_MODEL"

# 모델 선택 (교육용 주석)
# 기본: gemini-2.5-flash (현재 API에서 사용 가능)
# GEMINI_MODEL 환경 변수로 다른 모델 지정 가능
DEFAULT_MODEL = "gemini-2.5-flash"

# API 실패 시 각 필드에 넣을 기본값
FALLBACK_AI_SUMMARY = "요약을 생성하지 못했습니다."
FALLBACK_WHY_IT_MATTERS = "분석을 생성하지 못했습니다."
FALLBACK_KEYWORDS: list[str] = []


def _get_client():
    """환경 변수 GEMINI_API_KEY를 사용해 Gemini 클라이언트를 만듭니다."""
    from google import genai

    api_key = os.environ.get(ENV_API_KEY)
    if not api_key or not str(api_key).strip():
        raise ValueError(
            f"환경 변수 {ENV_API_KEY}가 설정되지 않았습니다. "
            "Google AI Studio에서 API 키를 발급받아 설정해 주세요."
        )
    return genai.Client(api_key=api_key.strip())


def _get_model_name() -> str:
    """사용할 모델 이름을 반환합니다. GEMINI_MODEL이 있으면 사용, 없으면 기본값."""
    return (os.environ.get(ENV_MODEL) or "").strip() or DEFAULT_MODEL


def _build_articles_text(news_items: list[dict]) -> str:
    """LLM에 넘길 때 쓰기 위해, 뉴스 목록을 번호 붙인 텍스트로 만듭니다."""
    lines = []
    for i, item in enumerate(news_items, start=1):
        title = item.get("title") or "(제목 없음)"
        link = item.get("link") or ""
        summary = item.get("summary") or ""
        published = item.get("published") or ""
        block = f"[기사 {i}]\n제목: {title}\n링크: {link}\n발행: {published}\n요약/본문: {summary}"
        lines.append(block)
    return "\n\n".join(lines)


def _build_prompt(news_items: list[dict]) -> str:
    """구조화된 지시문으로 프롬프트를 만듭니다. 응답을 JSON으로 고정해 파싱을 안정적으로 합니다."""
    articles_text = _build_articles_text(news_items)
    n = len(news_items)

    return f"""아래는 뉴스 기사 {n}개의 제목·링크·요약(또는 본문 일부)입니다.
각 기사에 대해 다음 세 가지를 생성해 주세요.

1. ai_summary: 기사를 2~3문장으로 요약 (한국어)
2. why_it_matters: "왜 중요한가"를 1~2문장으로 (한국어)
3. keywords: 기사와 관련된 키워드 3~5개 (한국어, 리스트)

반드시 아래 규칙을 지키세요.
- 응답은 반드시 JSON 배열 하나만 출력하세요. 다른 설명이나 마크다운 코드블록 없이 JSON만 출력합니다.
- 배열 길이는 정확히 {n}개입니다.
- 각 요소는 반드시 다음 키만 가집니다: "ai_summary", "why_it_matters", "keywords"
- "keywords"는 문자열의 배열입니다.
- 기사 순서는 [기사 1], [기사 2], ... 순서와 동일하게 유지합니다.

--- 뉴스 목록 ---

{articles_text}

--- JSON 배열 (위 지시대로) ---
"""


def _parse_summary_response(response_text: str, expected_count: int) -> list[dict] | None:
    """
    모델 응답 문자열에서 JSON 배열을 추출해 파싱합니다.
    실패하면 None을 반환합니다.
    """
    if not response_text or not isinstance(response_text, str):
        return None

    # 마크다운 코드블록 제거 (```json ... ``` 등)
    text = response_text.strip()
    if "```" in text:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if match:
            text = match.group(1).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning("요약 응답 JSON 파싱 실패: %s", e)
        return None

    if not isinstance(data, list) or len(data) != expected_count:
        logger.warning("요약 응답이 기대한 길이의 배열이 아님: len=%s, expected=%s", len(data) if isinstance(data, list) else "N/A", expected_count)
        return None

    # 각 항목이 필요한 키를 가지는지 확인하고, 형식이 맞으면 사용
    result = []
    for i, row in enumerate(data):
        if not isinstance(row, dict):
            return None
        ai_summary = row.get("ai_summary")
        why_it_matters = row.get("why_it_matters")
        keywords = row.get("keywords")
        if ai_summary is not None and not isinstance(ai_summary, str):
            ai_summary = str(ai_summary)
        if why_it_matters is not None and not isinstance(why_it_matters, str):
            why_it_matters = str(why_it_matters)
        if keywords is not None and not isinstance(keywords, list):
            keywords = [str(k) for k in keywords] if isinstance(keywords, (list, tuple)) else []
        result.append({
            "ai_summary": ai_summary if isinstance(ai_summary, str) else FALLBACK_AI_SUMMARY,
            "why_it_matters": why_it_matters if isinstance(why_it_matters, str) else FALLBACK_WHY_IT_MATTERS,
            "keywords": keywords if isinstance(keywords, list) else FALLBACK_KEYWORDS,
        })
    return result


def _apply_fallback_to_items(news_items: list[dict]) -> list[dict]:
    """각 뉴스 항목에 fallback 메시지로 ai_summary, why_it_matters, keywords를 붙여 반환합니다."""
    result = []
    for item in list(news_items):
        new_item = dict(item)
        new_item["ai_summary"] = FALLBACK_AI_SUMMARY
        new_item["why_it_matters"] = FALLBACK_WHY_IT_MATTERS
        new_item["keywords"] = list(FALLBACK_KEYWORDS)
        result.append(new_item)
    return result


def summarize_news_items(news_items: list[dict]) -> list[dict]:
    """
    뉴스 목록에 대해 Gemini로 요약·분석을 수행하고, 결과 필드를 붙인 목록을 반환합니다.

    - 입력: 뉴스 dict의 리스트 (각 dict에는 title, link, summary 등이 있음)
    - 출력: 각 항목에 ai_summary, why_it_matters, keywords가 추가된 새 리스트
    - API 키 없음/실패/파싱 실패 시: fallback 메시지가 들어간 목록을 반환 (예외 없음)
    """
    if not news_items:
        return []

    # 1) 클라이언트 생성 (API 키 없으면 여기서 ValueError)
    try:
        client = _get_client()
    except ValueError as e:
        logger.warning("Gemini 클라이언트 생성 실패: %s", e)
        return _apply_fallback_to_items(news_items)

    model_name = _get_model_name()
    prompt = _build_prompt(news_items)

    # 2) API 호출
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )
    except Exception as e:
        logger.exception("Gemini API 호출 실패: %s", e)
        return _apply_fallback_to_items(news_items)

    # 3) 응답 텍스트 추출 (SDK에 따라 .text 또는 다른 속성)
    response_text = getattr(response, "text", None)
    if response_text is None and hasattr(response, "candidates") and response.candidates:
        part = response.candidates[0].content.parts[0] if response.candidates[0].content.parts else None
        response_text = getattr(part, "text", None) if part else None
    if not response_text:
        logger.warning("Gemini 응답에 텍스트가 없음")
        return _apply_fallback_to_items(news_items)

    # 4) JSON 파싱
    parsed = _parse_summary_response(response_text, expected_count=len(news_items))
    if not parsed:
        return _apply_fallback_to_items(news_items)

    # 5) 원본 항목에 요약 필드 병합
    result = []
    for item, summary_row in zip(news_items, parsed, strict=True):
        new_item = dict(item)
        new_item["ai_summary"] = summary_row["ai_summary"]
        new_item["why_it_matters"] = summary_row["why_it_matters"]
        new_item["keywords"] = list(summary_row["keywords"])
        result.append(new_item)

    return result
