import os

# ==========================================
# 1. 파일 내용 정의 (여기에 모든 코드가 들어있습니다)
# ==========================================

# [1] 메인 실행 파일 (main.py)
code_main = """import streamlit as st
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
        \"\"\"
        ### ✅ 업무 시작 방법
        왼쪽 사이드바에서 **'🤖 AI행정관'** 메뉴를 클릭하세요.
        
        - **AI 행정관:** 법령 분석 및 공문서 초안 작성
        - **관리자:** (Admin 계정 전용) 시스템 통계 및 설정
        \"\"\"
    )
else:
    login_form()
"""

# [2] 스타일 정의 (src/ui/style.py)
code_style = """import streamlit as st

def apply_custom_style():
    st.markdown(\"\"\"
    <style>
        .stApp { background-color: #f8f9fa; font-family: 'Pretendard', sans-serif; }
        
        /* 공문서 종이 스타일 */
        .paper-sheet {
            background-color: white; width: 100%; padding: 40px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1); border-radius: 5px;
            font-family: 'Batang', serif; color: #111; line-height: 1.8;
            border: 1px solid #ddd;
        }
        .doc-header { text-align: center; font-size: 26px; font-weight: 900; margin-bottom: 30px; letter-spacing: 2px; }
        .doc-info { border-bottom: 2px solid #333; margin-bottom: 20px; padding-bottom: 10px; font-size: 14px;}
        
        /* 2분할 컨테이너 스타일 */
        div[data-testid="column"] {
            background-color: #ffffff;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            border: 1px solid #eee;
        }
        
        /* 사이드바 */
        [data-testid="stSidebar"] { background-color: #f1f3f5; }
    </style>
    \"\"\", unsafe_allow_html=True)
"""

# [3] 레이아웃 정의 (src/ui/layout.py) - 가로 2분할 기능 포함
code_layout = """import streamlit as st

def render_two_column_analysis(law_text: str, news_text: str):
    \"\"\"
    [기능] 법령과 뉴스 결과를 가로 2분할(1:1)로 보여줌
    \"\"\"
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
    \"\"\"공문서 미리보기 렌더링\"\"\"
    if not doc_data: return
    
    st.markdown(f\"\"\"
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
    \"\"\", unsafe_allow_html=True)
"""

# [4] 인증 서비스 (src/services/auth.py)
code_auth = """import streamlit as st
import time

def login_form():
    \"\"\"로그인 UI 및 로직\"\"\"
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
"""

# [5] AI 에이전트 로직 (src/services/llm_agent.py)
code_agent = """import time

class AI_Agent:
    \"\"\"
    실제 AI 연결 로직이 들어갈 자리입니다.
    지금은 폴더 구조 테스트를 위해 가짜 응답을 줍니다.
    나중에 여기에 Gemini/Groq 코드를 넣으면 됩니다.
    \"\"\"
    def analyze_law(self, query):
        time.sleep(1) # AI 생각하는 척
        return f"✅ **도로교통법 제32조 (정차 및 주차의 금지)**\\n\\n모든 차의 운전자는 교차로, 횡단보도, 건널목이나 보도와 차도가 구분된 도로의 보도... (중략) ... 주차하여서는 아니 된다.\\n\\n🔍 **분석:** '{query}' 상황은 위 조항에 명백히 위배됩니다."

    def search_news(self, query):
        time.sleep(1)
        return f"📰 **[판례] 불법주정차 과태료 부과 처분 취소 청구**\\n\\n- 사건번호: 2023구합1234\\n- 결과: 기각 (행정청 승소)\\n- 요지: 단속 사진의 시각 표시가 명확하므로 처분은 적법하다."

    def draft_document(self, query):
        return {
            "title": "과태료 부과 사전통지서",
            "receiver": "위반차량 소유주 귀하",
            "ref": "교통지도팀장",
            "body_paragraphs": f"1. 귀하의 가정에 평안을 기원합니다.\\n\\n2. 귀하의 차량이 {query} 위반 사실이 영상단속 장치에 의해 확인되었습니다.\\n\\n3. 이에 따라 도로교통법 제160조에 의거하여 과태료 부과를 사전 통지하오니, 이의가 있을 경우 기한 내 의견을 제출하여 주시기 바랍니다.",
            "department_head": "충 주 시 장"
        }

# 인스턴스 생성
agent = AI_Agent()
"""

# [6] 실무자 페이지 (pages/01_🤖_AI행정관.py)
code_page_admin_bot = """import streamlit as st
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
"""

# [7] 관리자 페이지 (pages/99_🔐_관리자.py)
code_page_dashboard = """import streamlit as st
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
"""

# [8] 의존성 파일 (requirements.txt)
code_req = """streamlit
pandas
google-generativeai
groq
supabase
"""

# ==========================================
# 2. 파일 생성 로직
# ==========================================
structure = {
    "main.py": code_main,
    "requirements.txt": code_req,
    "pages/01_🤖_AI행정관.py": code_page_admin_bot,
    "pages/99_🔐_관리자.py": code_page_dashboard,
    "src/__init__.py": "",
    "src/ui/__init__.py": "",
    "src/ui/style.py": code_style,
    "src/ui/layout.py": code_layout,
    "src/services/__init__.py": "",
    "src/services/auth.py": code_auth,
    "src/services/llm_agent.py": code_agent,
}

print("🚀 충주시청 AI 행정관 프로젝트 생성을 시작합니다...")

for path, content in structure.items():
    # 폴더가 포함된 경우 폴더부터 생성
    if "/" in path:
        os.makedirs(os.path.dirname(path), exist_ok=True)
    
    # 파일 쓰기
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ 생성 완료: {path}")

print("\\n🎉 모든 파일이 생성되었습니다!")
print("👉 실행 방법: streamlit run main.py")