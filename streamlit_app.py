# streamlit_app.py
# -*- coding: utf-8 -*-

import urllib.parse
import streamlit as st
import streamlit.components.v1 as components


LAW_BOT_SEARCH_URL = "https://www.law.go.kr/LSW/ais/searchList.do?query="


def make_lawbot_url(query: str) -> str:
    q = (query or "").strip()
    return LAW_BOT_SEARCH_URL + urllib.parse.quote(q)


st.set_page_config(page_title="Lawbot 검색 연동", page_icon="⚖️", layout="wide")
st.title("⚖️ Streamlit → Lawbot 검색 연동")
st.caption("검색어(문장 가능)를 넣고 버튼을 누르면 Lawbot 검색창에 입력된 상태로 결과 페이지가 열립니다.")

colL, colR = st.columns([1.2, 1])

with colL:
    query = st.text_area(
        "검색어 / 문장",
        height=120,
        placeholder="예: 무단방치 차량 처리부터 행정절차까지",
    )

    extra = st.text_input("추가 키워드(선택)", placeholder="예: 공시송달, 강제처리, 과태료")

    # 합쳐서 하나의 질의로
    final_query = query.strip()
    if extra.strip():
        final_query = f"{final_query} {extra.strip()}".strip()

    st.write("**최종 질의:**", final_query if final_query else "(비어있음)")

with colR:
    st.markdown("### 열기 방식")
    open_mode = st.radio(
        "선택",
        ["새 탭/새 창으로 열기(추천)", "현재 탭에서 바로 이동"],
        index=0,
    )

    st.markdown("### 사용 팁")
    st.markdown(
        "- ‘새 탭/새 창’은 **사용자 클릭 기반**이라 팝업 차단이 거의 없습니다.\n"
        "- ‘현재 탭 이동’은 Streamlit 화면을 떠나 Lawbot으로 바로 이동합니다.\n"
    )

st.divider()

if not final_query:
    st.info("왼쪽에 검색어/문장을 입력하세요.")
    st.stop()

lawbot_url = make_lawbot_url(final_query)

# 1) 추천: 사용자 클릭으로 열기 (팝업 차단 최소)
if open_mode.startswith("새"):
    st.link_button("🤖 Lawbot에서 검색 열기", lawbot_url, use_container_width=True)

# 2) 옵션: 현재 탭에서 즉시 이동
else:
    go = st.button("➡️ Lawbot으로 이동", use_container_width=True)
    if go:
        # 사용자 클릭 이벤트 이후 JS로 이동
        components.html(
            f"""
            <script>
              window.location.href = "{lawbot_url}";
            </script>
            """,
            height=0,
        )

with st.expander("🔗 생성된 Lawbot URL 보기(복사용)", expanded=False):
    st.code(lawbot_url, language="text")
