import streamlit as st

def render_two_column_analysis(law_text: str, news_text: str):
    """
    [기능] 법령과 뉴스 결과를 가로 2분할(1:1)로 보여줌
    """
    st.markdown("---")
    st.caption("📊 AI 분석 결과 상세 비교")
    
    # 1:1 비율로 컬럼 나누기
    col1, col2 = st.columns([1, 1], gap="medium")
    
    with col1:
        st.subheader("📜 법령 및 근거")
        with st.container(height=350, border=True):
            st.markdown(law_text if law_text else "관련 법령 없음")
            
    with col2:
        st.subheader("📰 유사 사례/뉴스")
        with st.container(height=350, border=True):
            st.markdown(news_text if news_text else "관련 뉴스 없음")

def render_doc_preview(doc_data: dict):
    """공문서 미리보기 렌더링"""
    if not doc_data: return
    
    st.markdown(f"""
    <div class="paper-sheet">
        <div class="doc-header">{doc_data.get('title', '공 문 서')}</div>
        <div class="doc-info">
            <b>수신:</b> {doc_data.get('receiver', '')}<br>
            <b>참조:</b> {doc_data.get('ref', '없음')}
        </div>
        <div style="white-space: pre-line; min-height: 300px;">
            {doc_data.get('body_paragraphs', '')}
        </div>
        <br><br><br>
        <div style="text-align:center; font-size:22px; font-weight:bold;">
            {doc_data.get('department_head', '행정기관장')}
        </div>
    </div>
    """, unsafe_allow_html=True)
