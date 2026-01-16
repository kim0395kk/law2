import streamlit as st
from src.services.auth import require_auth
from src.services.llm_agent import agent
from src.ui.layout import render_two_column_analysis, render_doc_preview
from src.ui.style import apply_custom_style

st.set_page_config(layout="wide", page_title="AI 행정관")
apply_custom_style()
require_auth()

st.title("🤖 AI 행정관 워크스페이스")

# 사이드바 입력
with st.sidebar:
    st.info(f"👤 사용자: {st.session_state['username']}")
    query = st.text_area("업무 지시 (상황/요청)", height=150, placeholder="예: 소화전 앞 불법주차 단속 공문 써줘.")
    
    if st.button("🚀 분석 및 생성", type="primary"):
        if query:
            with st.spinner("AI 에이전트가 법령을 분석하고 있습니다..."):
                # 서비스(로직) 호출
                law_res = agent.analyze_law(query)
                news_res = agent.search_news(query)
                doc_res = agent.draft_document(query)
                
                # 결과 저장
                st.session_state['result'] = {
                    "law": law_res, "news": news_res, "doc": doc_res
                }
        else:
            st.warning("내용을 입력해주세요.")

# 결과 화면
if "result" in st.session_state:
    res = st.session_state['result']
    
    # 1. 상단: 법령 vs 뉴스 (가로 2분할)
    render_two_column_analysis(res['law'], res['news'])
    
    st.divider()
    
    # 2. 하단: 공문서 미리보기
    st.subheader("📝 생성된 공문서 초안")
    render_doc_preview(res['doc'])
