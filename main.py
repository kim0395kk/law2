import streamlit as st
from src.services.auth import login_form

st.set_page_config(page_title="충주시청 AI 행정관", page_icon="🏢", layout="centered")

# 세션 초기화
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

# 메인 로직: 로그인 여부에 따라 화면 분기
if st.session_state["logged_in"]:
    st.sidebar.success(f"로그인 됨: {st.session_state.get('username')}")
    st.title("👋 환영합니다.")
    st.markdown(
        """
        ### ✅ 업무 시작 방법
        왼쪽 사이드바에서 **'🤖 AI행정관'** 메뉴를 클릭하세요.
        
        - **AI 행정관:** 법령 분석 및 공문서 초안 작성
        - **관리자:** (Admin 계정 전용) 시스템 통계 및 설정
        """
    )
else:
    login_form()
