import streamlit as st
import time

def login_form():
    """로그인 UI 및 로직"""
    st.markdown("## 🔐 AI 행정관 Pro")
    st.caption("충주시청 공무원 전용 시스템")
    
    with st.form("login_form"):
        user_id = st.text_input("아이디", placeholder="admin 또는 user")
        user_pw = st.text_input("비밀번호", type="password")
        submitted = st.form_submit_button("로그인", type="primary")
        
        if submitted:
            # [테스트용] admin/admin 또는 user/user
            if user_id in ["admin", "user"]:
                st.session_state["logged_in"] = True
                st.session_state["username"] = user_id
                st.session_state["role"] = "admin" if user_id == "admin" else "staff"
                st.success("로그인 성공! 잠시만 기다려주세요.")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("아이디를 확인하세요. (테스트: admin / user)")

def require_auth():
    if not st.session_state.get("logged_in"):
        st.warning("로그인이 필요한 페이지입니다.")
        st.stop()

def require_admin():
    require_auth()
    if st.session_state.get("role") != "admin":
        st.error("⛔ 접근 권한이 없습니다. (관리자 전용)")
        st.stop()
