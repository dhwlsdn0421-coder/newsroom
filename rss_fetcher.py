"""
RSS 피드 수집 모듈.

명세: docs/RSS_수집_명세서.md
"""

import logging
import re
from typing import Any

import feedparser
import requests

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 15
MAX_RESPONSE_BYTES = 5 * 1024 * 1024  # 5MB
LIMIT_MIN = 1
LIMIT_MAX = 100


def _validate_and_normalize_inputs(feed_url: Any, limit: Any) -> tuple[str, int]:
    """입력 검증 및 limit 보정. 위반 시 ValueError."""
    if feed_url is None:
        raise ValueError("feed_url은 None일 수 없습니다.")
    if not isinstance(feed_url, str):
        raise ValueError("feed_url은 문자열이어야 합니다.")
    url = feed_url.strip()
    if not url:
        raise ValueError("feed_url이 비어 있습니다.")
    if not (url.startswith("http://") or url.startswith("https://")):
        raise ValueError("feed_url은 http:// 또는 https://로 시작해야 합니다.")

    try:
        n = int(limit)
    except (TypeError, ValueError):
        n = LIMIT_MIN
    if n < LIMIT_MIN:
        n = LIMIT_MIN
    elif n > LIMIT_MAX:
        n = LIMIT_MAX

    return url, n


def _fetch_feed_bytes(url: str) -> bytes:
    """URL에서 RSS raw 데이터를 가져옵니다. 타임아웃·크기 제한 적용."""
    resp = requests.get(url, timeout=DEFAULT_TIMEOUT, stream=True)
    resp.raise_for_status()
    content = b""
    for chunk in resp.iter_content(chunk_size=65536):
        content += chunk
        if len(content) > MAX_RESPONSE_BYTES:
            break
    return content[:MAX_RESPONSE_BYTES]


def _strip_html(html: str) -> str:
    """HTML 태그를 제거한 순수 텍스트를 반환합니다."""
    if not html or not isinstance(html, str):
        return ""
    text = re.sub(r"<[^>]+>", "", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _format_published(entry: Any) -> str | None:
    """entry에서 발행일을 ISO 8601 문자열 또는 None으로 반환합니다."""
    try:
        if getattr(entry, "published_parsed", None):
            import time
            t = entry.published_parsed
            if t and len(t) >= 6:
                return f"{t.tm_year:04d}-{t.tm_mon:02d}-{t.tm_mday:02d}T{t.tm_hour:02d}:{t.tm_min:02d}:{t.tm_sec:02d}Z"
        if getattr(entry, "published", None):
            s = entry.published
            if isinstance(s, str) and s.strip():
                return s.strip()
    except Exception:
        pass
    return None


def _entry_to_article(entry: Any) -> dict:
    """feedparser entry를 명세 스키마의 기사 dict로 변환합니다."""
    title = ""
    if getattr(entry, "title", None) is not None:
        title = str(entry.title).strip()

    link = ""
    if getattr(entry, "link", None) is not None:
        link = str(entry.link).strip()

    published = _format_published(entry)

    summary = None
    if getattr(entry, "summary", None) is not None:
        raw = entry.summary
        if isinstance(raw, str):
            summary = _strip_html(raw) or None

    return {
        "title": title,
        "link": link,
        "published": published,
        "summary": summary,
    }


def _validate_parsed_feed(feed: Any) -> list:
    """
    파싱 결과를 검증합니다.
    - bozo이고 entries를 쓸 수 없으면 ValueError.
    - entries 없음 또는 리스트 아님 → 빈 리스트.
    - bozo이지만 entries 존재 → entries 반환(로깅만).
    """
    entries = getattr(feed, "entries", None)
    if not isinstance(entries, list):
        return []
    bozo = getattr(feed, "bozo", False)
    if bozo and not entries:
        msg = getattr(feed, "bozo_exception", None)
        err = str(msg) if msg else "알 수 없는 파싱 오류"
        logger.warning("RSS 파싱 경고(entries 없음): %s", err)
        raise ValueError(f"RSS 파싱 실패: {err}")
    if bozo and entries:
        logger.warning("RSS 파싱 경고(부분 성공, entries 사용): %s", getattr(feed, "bozo_exception", ""))
    return entries


def _dedupe_by_link(articles: list[dict]) -> list[dict]:
    """동일 link는 처음 등장한 것만 유지합니다."""
    seen: set[str] = set()
    out: list[dict] = []
    for a in articles:
        link = a.get("link", "")
        if link not in seen:
            seen.add(link)
            out.append(a)
    return out


def fetch_rss_items(feed_url: str, limit: int = 5) -> list[dict]:
    """
    RSS 피드 주소로부터 최신 기사 목록을 수집합니다.

    Args:
        feed_url: RSS 주소 (http:// 또는 https://)
        limit: 수집할 기사 개수 상한 (1~100, 범위 밖은 보정)

    Returns:
        기사 정보(dict) 리스트. 각 dict는 title, link, published, summary 키를 가짐.
        최신순, 동일 link 중복 제거 후 limit개까지.

    Raises:
        ValueError: feed_url 검증 실패 또는 RSS 파싱 실패(entries 없음)
        requests.RequestException: 네트워크 오류(연결 실패, 타임아웃, HTTP 4xx/5xx)
        UnicodeDecodeError / ValueError: 응답 인코딩 오류
    """
    url, n = _validate_and_normalize_inputs(feed_url, limit)

    try:
        raw = _fetch_feed_bytes(url)
    except requests.RequestException as e:
        logger.exception("RSS 가져오기 실패: %s", url)
        raise

    try:
        content = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as e:
        logger.exception("RSS 응답 디코딩 실패: %s", url)
        raise ValueError(f"RSS 응답 인코딩 오류: {e}") from e

    feed = feedparser.parse(content)
    entries = _validate_parsed_feed(feed)

    articles = [_entry_to_article(e) for e in entries]
    articles.sort(key=lambda a: (a.get("published") or ""), reverse=True)
    articles = _dedupe_by_link(articles)
    return articles[:n]
