import streamlit as st
import pandas as pd
from src.services.auth import require_admin
from src.ui.style import apply_custom_style

st.set_page_config(layout="wide", page_title="관리자 대시보드")
apply_custom_style()
require_admin() # 관리자만 접근 가능

st.title("🔐 시스템 관리자 대시보드")
st.caption("AI 행정관 시스템의 사용 현황을 모니터링합니다.")

# 대시보드 메트릭
col1, col2, col3 = st.columns(3)
col1.metric("오늘 생성된 공문", "128건", "+12건")
col2.metric("AI 토큰 비용", "₩12,500", "-5%")
col3.metric("승인 대기 사용자", "3명", "action required")

st.divider()

col_chart, col_log = st.columns([2, 1])

with col_chart:
    st.subheader("📊 부서별 AI 활용도")
    data = pd.DataFrame({
        '부서': ['도로과', '건축과', '민원봉사과', '세무과'],
        '사용횟수': [45, 30, 82, 15]
    })
    st.bar_chart(data.set_index('부서'))

with col_log:
    st.subheader("📢 시스템 공지")
    st.info("내일(1/20) 새벽 2시 서버 점검 예정입니다.")
    st.warning("Supabase 스토리지 용량이 80% 도달했습니다.")
