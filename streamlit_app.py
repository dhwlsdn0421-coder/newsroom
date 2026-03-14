"""
나만의 뉴스룸 – Streamlit 앱 (교육용)

실행 방법 (프로젝트 루트에서):
  streamlit run streamlit_app.py

구조:
- 상단: 환경 로드, import
- 로직 보조: RSS 수집·요약 파이프라인, 기사 데이터 정규화
- UI 보조: 기사 카드 한 장 그리기
- 메인: 입력 폼 → 버튼 시 파이프라인 호출 → 결과/에러 표시
"""

from pathlib import Path
import os
import streamlit as st
from dotenv import load_dotenv

from rss_fetcher import fetch_rss_items
from app.services.summary_service import summarize_news_items, FALLBACK_AI_SUMMARY

# ---------------------------------------------------------------------------
# 설정·상수 (숫자/문자열을 한곳에 두어 수정하기 쉽게)
# ---------------------------------------------------------------------------
PAGE_TITLE = "나만의 뉴스룸"
SLIDER_MIN, SLIDER_MAX, SLIDER_DEFAULT = 1, 10, 5
RSS_PLACEHOLDER = "https://example.com/feed.xml"
TITLE_FALLBACK = "(제목 없음)"
MAX_BADGES_PER_ROW = 8
TITLE_PREVIEW_LEN = 50


def _load_config() -> None:
    """
    API 키 등 설정 로드.
    - 배포(Streamlit Cloud 등): st.secrets 사용 (.streamlit/secrets.toml 또는 플랫폼 시크릿)
    - 로컬: .env 사용 (st.secrets에 키가 없을 때)
    summary_service는 os.environ을 보므로, 여기서 둘 중 하나를 env에 넣는다.
    """
    env_path = Path(__file__).resolve().parent / ".env"
    try:
        if hasattr(st, "secrets"):
            key = st.secrets.get("GEMINI_API_KEY")
            if key and str(key).strip():
                os.environ["GEMINI_API_KEY"] = str(key).strip()
            model = st.secrets.get("GEMINI_MODEL")
            if model and str(model).strip():
                os.environ["GEMINI_MODEL"] = str(model).strip()
            if os.environ.get("GEMINI_API_KEY"):
                return
    except Exception:
        pass
    load_dotenv(env_path)


# 앱 시작 전에 한 번만 로드
_load_config()


# ---------------------------------------------------------------------------
# 로직 보조 (Streamlit과 무관: 데이터만 다룸)
# ---------------------------------------------------------------------------

def fetch_and_summarize(rss_url: str, limit: int) -> list[dict]:
    """
    RSS 주소에서 기사를 가져온 뒤 AI 요약을 붙여 반환한다.

    Returns:
        요약이 붙은 기사 dict 리스트 (각 항목에 title, link, ai_summary 등 포함)

    Raises:
        ValueError: URL이 비어 있거나 형식이 잘못됨, 또는 RSS 파싱 실패
        Exception: 네트워크 오류 등 (메시지는 호출 쪽에서 사용자에게 표시)
    """
    url = (rss_url or "").strip()
    if not url:
        raise ValueError("RSS 주소를 입력해 주세요.")

    articles = fetch_rss_items(url, limit)

    if not articles:
        raise ValueError("가져온 기사가 없습니다. RSS 주소를 확인해 주세요.")

    return summarize_news_items(articles)


def _article_display_data(article: dict) -> dict:
    """
    기사 dict에서 화면에 쓸 값을 꺼내 기본값을 채워 반환한다.
    UI에서 .get() 반복을 줄이기 위한 보조 함수.
    """
    return {
        "title": article.get("title") or TITLE_FALLBACK,
        "link": article.get("link") or "",
        "published": article.get("published") or "",
        "ai_summary": article.get("ai_summary") or "",
        "why_it_matters": article.get("why_it_matters") or "",
        "keywords": article.get("keywords") or [],
    }


# ---------------------------------------------------------------------------
# UI 보조 (한 장의 기사 카드를 그리는 함수)
# ---------------------------------------------------------------------------

def _render_article_card(article_data: dict, index: int) -> None:
    """
    기사 한 건을 expander + 제목·링크·요약·키워드로 그린다.
    Streamlit 위젯을 사용하므로 이 함수는 UI 코드다.
    """
    title = article_data["title"]
    link = article_data["link"]
    published = article_data["published"]
    ai_summary = article_data["ai_summary"]
    why_it_matters = article_data["why_it_matters"]
    keywords = article_data["keywords"]

    # expander 제목: 길면 잘라서 표시
    preview = title[:TITLE_PREVIEW_LEN] + ("…" if len(title) > TITLE_PREVIEW_LEN else "")
    expander_label = f"기사 {index}: {preview}"

    with st.expander(expander_label, expanded=True):
        st.subheader(title)
        if published:
            st.caption(f"발행: {published}")
        if link:
            try:
                st.link_button("기사 링크 열기", url=link, type="primary")
            except (TypeError, AttributeError):
                st.markdown(f"🔗 [기사 링크 열기]({link})")
        st.markdown("**요약**")
        st.write(ai_summary)
        st.markdown("**왜 중요한가**")
        st.write(why_it_matters)
        if keywords:
            st.caption("키워드")
            try:
                n = min(len(keywords), MAX_BADGES_PER_ROW)
                cols = st.columns(n)
                for col, kw in zip(cols, keywords[:n]):
                    with col:
                        st.badge(kw)
                if len(keywords) > MAX_BADGES_PER_ROW:
                    st.caption(", ".join(keywords[MAX_BADGES_PER_ROW:]))
            except AttributeError:
                st.markdown(" ".join(f"`{k}`" for k in keywords))


# ---------------------------------------------------------------------------
# 메인 UI
# ---------------------------------------------------------------------------

st.set_page_config(page_title=PAGE_TITLE, layout="wide")
st.title(PAGE_TITLE)

# 입력
rss_url = st.text_input("RSS 주소", placeholder=RSS_PLACEHOLDER)
article_count = st.slider("기사 개수", min_value=SLIDER_MIN, max_value=SLIDER_MAX, value=SLIDER_DEFAULT)
submit = st.button("뉴스 요약하기")

if not submit:
    st.info("RSS 주소와 기사 개수를 선택한 뒤 '뉴스 요약하기' 버튼을 눌러 주세요.")
    st.stop()

# 버튼을 눌렀을 때: 로직 호출 → 결과 또는 에러 표시
error_zone = st.container()
result_zone = st.container()

with error_zone:
    try:
        with st.spinner("RSS를 가져오는 중…"):
            raw_result = fetch_and_summarize(rss_url, article_count)
    except ValueError as e:
        st.error(str(e))
        st.info("RSS 주소는 http:// 또는 https:// 로 시작해야 합니다.")
        st.stop()
    except Exception as e:
        st.error("RSS를 가져오지 못했습니다.")
        st.error(f"자세한 내용: {e}")
        st.info("주소 확인과 인터넷 연결을 확인해 주세요.")
        st.stop()

# 결과가 있을 때만 결과 영역에 표시
with result_zone:
    st.success(f"총 {len(raw_result)}개의 기사를 요약했습니다.")
    # 요약이 하나도 생성되지 않았으면 API 키/연결 안내 (교육용)
    all_fallback = all(
        (a.get("ai_summary") or "").strip() == FALLBACK_AI_SUMMARY for a in raw_result
    )
    if all_fallback:
        st.warning(
            "**요약·분석이 생성되지 않았습니다.**\n\n"
            "가능한 이유: (1) 프로젝트 루트의 `.env`에 `GEMINI_API_KEY`가 없거나 잘못됨 "
            "(2) API 키 한도 초과 또는 네트워크 오류. "
            ".env 파일을 확인한 뒤 서버를 다시 실행해 보세요."
        )
    for i, article in enumerate(raw_result, start=1):
        data = _article_display_data(article)
        _render_article_card(data, i)
