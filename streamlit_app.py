import streamlit as st
import google.generativeai as genai
from groq import Groq
from supabase import create_client
import json
import re
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from html import escape as _escape

# ==========================================
# 0) Settings & Config
# ==========================================
st.set_page_config(layout="wide", page_title="AI 행정관 Pro: LawBot", page_icon="⚖️")
MAX_FOLLOWUP_Q = 5 

# 스타일: Lawbot 테마 + 사이드바 스타일링
st.markdown(
    """
<style>
    /* 전체 배경 및 폰트 */
    .stApp { background-color: #f8f9fa; font-family: 'Pretendard', sans-serif; }
    
    /* 사이드바 스타일 (Gemini 느낌) */
    [data-testid="stSidebar"] {
        background-color: #f0f2f6;
        border-right: 1px solid #e0e0e0;
    }
    
    /* 공문서 용지 스타일 */
    .paper-sheet {
        background-color: white;
        width: 100%;
        max-width: 210mm;
        min-height: 297mm;
        padding: 25mm;
        margin: auto;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        font-family: 'Batang', serif;
        color: #111;
        line-height: 1.6;
        position: relative;
    }

    .doc-header { text-align: center; font-size: 22pt; font-weight: 900; margin-bottom: 30px; letter-spacing: 2px; }
    .doc-info { display: flex; justify-content: space-between; font-size: 11pt; border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 20px; gap:10px; flex-wrap:wrap; }
    .doc-body { font-size: 12pt; text-align: justify; white-space: pre-line; }
    .doc-footer { text-align: center; font-size: 20pt; font-weight: bold; margin-top: 80px; letter-spacing: 5px; }
    .stamp { position: absolute; bottom: 85px; right: 80px; border: 3px solid #cc0000; color: #cc0000; padding: 5px 10px; font-size: 14pt; font-weight: bold; transform: rotate(-15deg); opacity: 0.8; border-radius: 5px; }

    /* 로그 스타일 */
    .agent-log { font-family: 'Consolas', monospace; font-size: 0.85rem; padding: 6px 12px; border-radius: 6px; margin-bottom: 8px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
    .log-legal { background-color: #eff6ff; color: #1e40af; border-left: 4px solid #3b82f6; }
    .log-search { background-color: #fff7ed; color: #c2410c; border-left: 4px solid #f97316; }
    .log-strat { background-color: #f5f3ff; color: #6d28d9; border-left: 4px solid #8b5cf6; }
    .log-calc { background-color: #f0fdf4; color: #166534; border-left: 4px solid #22c55e; }
    .log-draft { background-color: #fef2f2; color: #991b1b; border-left: 4px solid #ef4444; }
    
    /* Streamlit 기본 UI 숨김 */
    header [data-testid="stToolbar"] { display: none !important; }
    header [data-testid="stDecoration"] { display: none !important; }
    header { height: 0px !important; }
    footer { display: none !important; }
    div[data-testid="stStatusWidget"] { display: none !important; }
    
    /* 로그인 박스 스타일 */
    .login-container {
        max-width: 400px;
        margin: 100px auto;
        padding: 40px;
        background: white;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        text-align: center;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ==========================================
# 2) Infrastructure Services
# ==========================================

class LLMService:
    def __init__(self):
        g = st.secrets.get("general", {})
        self.gemini_key = g.get("GEMINI_API_KEY")
        self.groq_key = g.get("GROQ_API_KEY")

        self.gemini_models = [
            "gemini-2.0-flash-exp", # 최신 모델 우선
            "gemini-1.5-flash",
        ]

        if self.gemini_key:
            genai.configure(api_key=self.gemini_key)

        self.groq_client = Groq(api_key=self.groq_key) if self.groq_key else None

    def _try_gemini(self, prompt, is_json=False, schema=None):
        for model_name in self.gemini_models:
            try:
                model = genai.GenerativeModel(model_name)
                config = genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                ) if is_json else None
                res = model.generate_content(prompt, generation_config=config)
                return res.text, model_name
            except Exception:
                continue
        raise Exception("All Gemini models failed")

    def generate_text(self, prompt):
        try:
            text, _ = self._try_gemini(prompt, is_json=False)
            return text
        except Exception:
            if self.groq_client:
                return self._generate_groq(prompt)
            return "시스템 오류: AI 모델 연결 실패"

    def generate_json(self, prompt, schema=None):
        try:
            text, _ = self._try_gemini(prompt, is_json=True, schema=schema)
            return json.loads(text)
        except Exception:
            text = self.generate_text(prompt + "\n\nOutput strictly in JSON.")
            try:
                match = re.search(r"\{.*\}|\[.*\]", text, re.DOTALL)
                return json.loads(match.group(0)) if match else None
            except Exception:
                return None

    def _generate_groq(self, prompt):
        try:
            completion = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            return completion.choices[0].message.content
        except Exception:
            return "System Error"


class SearchService:
    def __init__(self):
        g = st.secrets.get("general", {})
        self.client_id = g.get("NAVER_CLIENT_ID")
        self.client_secret = g.get("NAVER_CLIENT_SECRET")
        self.news_url = "https://openapi.naver.com/v1/search/news.json"

    def _headers(self):
        return {"X-Naver-Client-Id": self.client_id, "X-Naver-Client-Secret": self.client_secret}

    def _clean_html(self, s: str) -> str:
        if not s: return ""
        s = re.sub(r"<[^>]+>", "", s)
        s = re.sub(r"&quot;", '"', s)
        s = re.sub(r"&lt;", "<", s)
        s = re.sub(r"&gt;", ">", s)
        s = re.sub(r"&amp;", "&", s)
        return s.strip()

    def _extract_keywords_llm(self, situation: str) -> str:
        prompt = f"상황: '{situation}'\n뉴스 검색을 위한 핵심 키워드 2개만 콤마로 구분해 출력."
        try:
            res = llm_service.generate_text(prompt).strip()
            return re.sub(r'[".?]', "", res)
        except Exception:
            return situation[:20]

    def search_news(self, query: str, top_k: int = 3) -> str:
        if not self.client_id or not self.client_secret: return "⚠️ 네이버 API 키 없음"
        if not query: return "⚠️ 검색어 없음"

        try:
            params = {"query": query, "display": 10, "sort": "sim"}
            res = requests.get(self.news_url, headers=self._headers(), params=params, timeout=8)
            res.raise_for_status()
            items = res.json().get("items", [])
            if not items: return f"🔍 `{query}` 관련 검색 결과 없음."

            lines = [f"📰 **최신 뉴스 사례 (검색어: {query})**", "---"]
            for it in items[:top_k]:
                title = self._clean_html(it.get("title", ""))
                desc = self._clean_html(it.get("description", ""))
                link = it.get("link", "#")
                lines.append(f"- **[{title}]({link})**\n  : {desc[:150]}...")
            return "\n".join(lines)
        except Exception as e:
            return f"검색 오류: {str(e)}"

    def search_precedents(self, situation: str, top_k: int = 3) -> str:
        keywords = self._extract_keywords_llm(situation)
        return self.search_news(keywords, top_k=top_k)


class DatabaseService:
    def __init__(self):
        try:
            self.url = st.secrets["supabase"]["SUPABASE_URL"]
            self.key = st.secrets["supabase"].get("SUPABASE_KEY") or st.secrets["supabase"].get("SUPABASE_ANON_KEY")
            self.client = create_client(self.url, self.key)
            self.is_active = True
        except Exception:
            self.is_active = False
            self.client = None

    def _pack_summary(self, res: dict, followup: dict) -> str:
        payload = {
            "meta": res.get("meta"),
            "strategy": res.get("strategy"),
            "search_initial": res.get("search"),
            "law_initial": res.get("law"),
            "document_content": res.get("doc"),
            "followup": followup,
        }
        return json.dumps(payload, ensure_ascii=False)

    # 🟢 [기능 추가] 사용자별 과거 기록 조회
    def fetch_history(self, username: str):
        if not self.is_active or not username:
            return []
        try:
            # DB에 'username' 컬럼이 있다고 가정 (없으면 에러 날 수 있으니 체크 필요)
            # 여기서는 편의상 situation 컬럼 등을 가져옵니다.
            resp = self.client.table("law_reports") \
                .select("id, created_at, situation, summary") \
                .eq("username", username) \
                .order("created_at", desc=True) \
                .limit(20) \
                .execute()
            return resp.data if resp.data else []
        except Exception as e:
            # st.error(f"히스토리 조회 실패: {e}")
            return []

    # 🟢 [기능 수정] 저장 시 username 포함
    def insert_initial_report(self, res: dict, username: str) -> dict:
        if not self.is_active:
            return {"ok": False, "msg": "DB 미연결", "id": None}

        try:
            followup = {"count": 0, "messages": [], "extra_context": ""}
            data = {
                "situation": res.get("situation", ""),
                "law_name": res.get("law", ""),
                "summary": self._pack_summary(res, followup),
                "username": username, # 사용자 식별용
            }
            resp = self.client.table("law_reports").insert(data).execute()
            
            inserted_id = None
            if hasattr(resp, "data") and resp.data:
                inserted_id = resp.data[0].get("id")
            return {"ok": True, "msg": "저장 성공", "id": inserted_id}
        except Exception as e:
            return {"ok": False, "msg": f"DB 저장 실패: {e}", "id": None}

    def update_followup(self, report_id, res: dict, followup: dict) -> dict:
        if not self.is_active or not report_id: return {"ok": False}
        summary = self._pack_summary(res, followup)
        try:
            self.client.table("law_reports").update({"summary": summary}).eq("id", report_id).execute()
            return {"ok": True}
        except Exception:
            return {"ok": False}


class LawOfficialService:
    def __init__(self):
        self.api_id = st.secrets.get("general", {}).get("LAW_API_ID")
        self.base_url = "http://www.law.go.kr/DRF/lawSearch.do"
        self.service_url = "http://www.law.go.kr/DRF/lawService.do"

    def _make_current_link(self, mst_id: str) -> str | None:
        if not self.api_id or not mst_id: return None
        return f"https://www.law.go.kr/DRF/lawService.do?OC={self.api_id}&target=law&MST={mst_id}&type=HTML"

    def get_law_text(self, law_name, article_num=None, return_link: bool = False):
        if not self.api_id:
            msg = "⚠️ API ID 설정 필요"
            return (msg, None) if return_link else msg

        try:
            params = {"OC": self.api_id, "target": "law", "type": "XML", "query": law_name, "display": 1}
            res = requests.get(self.base_url, params=params, timeout=6)
            root = ET.fromstring(res.content)
            law_node = root.find(".//law")
            if law_node is None:
                msg = f"🔍 '{law_name}' 검색 결과 없음"
                return (msg, None) if return_link else msg
            
            mst_id = (law_node.findtext("법령일련번호") or "").strip()
            current_link = self._make_current_link(mst_id)

            if not mst_id:
                return (f"✅ '{law_name}' 확인 (원문 링크 참고)", current_link) if return_link else "..."

            detail_params = {"OC": self.api_id, "target": "law", "type": "XML", "MST": mst_id}
            res_detail = requests.get(self.service_url, params=detail_params, timeout=10)
            root_detail = ET.fromstring(res_detail.content)

            if article_num:
                for article in root_detail.findall(".//조문단위"):
                    jo_num = (article.find("조문번호").text or "").strip()
                    if str(article_num) == jo_num:
                        content = article.find("조문내용").text or ""
                        txt = f"[{law_name} 제{jo_num}조]\n" + _escape(content.strip())
                        return (txt, current_link) if return_link else txt
            
            return (f"✅ {law_name} 제{article_num}조 (자동추출 실패, 링크 참조)", current_link) if return_link else "..."
        except Exception as e:
            return (f"API 오류: {e}", None) if return_link else str(e)


# ==========================================
# 3) Global Instances
# ==========================================
llm_service = LLMService()
search_service = SearchService()
db_service = DatabaseService()
law_api_service = LawOfficialService()


# ==========================================
# 4) Agents (Logic)
# ==========================================
class LegalAgents:
    @staticmethod
    def researcher(situation):
        prompt = f"""상황: "{situation}"\n관련 핵심 법령과 조문번호를 중요도순 최대 3개 JSON 리스트로 추출.\n형식: [{{"law_name": "도로교통법", "article_num": 32}}]"""
        try:
            targets = llm_service.generate_json(prompt)
            if not isinstance(targets, list): targets = []
        except: targets = []

        if not targets: targets = [{"law_name": "도로교통법", "article_num": None}]
        
        lines = [f"🔍 **AI 식별 법령 ({len(targets)}건)**", "---"]
        for idx, item in enumerate(targets):
            l_name = item.get("law_name", "법령")
            l_num = item.get("article_num")
            txt, link = law_api_service.get_law_text(l_name, l_num, return_link=True)
            link_md = f"[{l_name}]({link})" if link else l_name
            lines.append(f"✅ **{idx+1}. {link_md} 제{l_num}조**\n{txt}\n")
        return "\n".join(lines)

    @staticmethod
    def strategist(situation, legal_basis, search_results):
        prompt = f"""당신은 유능한 행정 주무관. 민원상황: {situation}\n법적근거: {legal_basis}\n유사사례: {search_results}\n\n처리방향(Strategy)을 수립하라. (서론 생략, 핵심만)"""
        return llm_service.generate_text(prompt)

    @staticmethod
    def clerk(situation, legal_basis):
        today = datetime.now()
        deadline = today + timedelta(days=15)
        return {
            "today_str": today.strftime("%Y. %m. %d."),
            "deadline_str": deadline.strftime("%Y. %m. %d."),
            "days_added": 15,
            "doc_num": f"행정-{today.strftime('%Y')}-{int(time.time())%1000:03d}호",
        }

    @staticmethod
    def drafter(situation, legal_basis, meta_info, strategy):
        schema = {
            "type": "OBJECT",
            "properties": {
                "title": {"type": "STRING"},
                "receiver": {"type": "STRING"},
                "body_paragraphs": {"type": "ARRAY", "items": {"type": "STRING"}},
                "department_head": {"type": "STRING"},
            },
            "required": ["title", "receiver", "body_paragraphs", "department_head"],
        }
        prompt = f"""행정 서기 역할. 공문서 작성.\n민원: {situation}\n법: {legal_basis}\n전략: {strategy}\n시행일: {meta_info['today_str']}\n\n위 내용을 바탕으로 공문서 JSON 작성."""
        return llm_service.generate_json(prompt, schema=schema)


# ==========================================
# 5) Workflow & Followup
# ==========================================
def run_workflow(user_input):
    log_placeholder = st.empty()
    logs = []
    def add_log(msg, style="sys"):
        logs.append(f"<div class='agent-log log-{style}'>{_escape(msg)}</div>")
        log_placeholder.markdown("".join(logs), unsafe_allow_html=True)
        time.sleep(0.2)

    add_log("🔍 Phase 1: 법령 및 유사 사례 리서치...", "legal")
    legal_basis = LegalAgents.researcher(user_input)
    
    add_log("🟩 네이버 뉴스 검색 가동...", "search")
    search_res = search_service.search_precedents(user_input)

    add_log("🧠 Phase 2: AI 주무관 처리 방향 수립...", "strat")
    strategy = LegalAgents.strategist(user_input, legal_basis, search_res)

    add_log("✍️ Phase 3: 공문서 작성 중...", "draft")
    meta = LegalAgents.clerk(user_input, legal_basis)
    doc = LegalAgents.drafter(user_input, legal_basis, meta, strategy)
    
    time.sleep(0.3)
    log_placeholder.empty()

    return {
        "situation": user_input,
        "doc": doc,
        "meta": meta,
        "law": legal_basis,
        "search": search_res,
        "strategy": strategy,
    }

def render_followup(res):
    if "followup_msgs" not in st.session_state: st.session_state["followup_msgs"] = []
    
    for m in st.session_state["followup_msgs"]:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    q = st.chat_input("이 공문에 대해 추가로 궁금한 점이 있나요?")
    if q:
        st.session_state["followup_msgs"].append({"role": "user", "content": q})
        with st.chat_message("user"): st.markdown(q)
        
        ctx = f"상황:{res['situation']}\n법:{res['law']}\n전략:{res['strategy']}\n질문:{q}"
        ans = llm_service.generate_text(ctx + "\n위 내용 기반으로 답변해.")
        
        with st.chat_message("assistant"): st.markdown(ans)
        st.session_state["followup_msgs"].append({"role": "assistant", "content": ans})
        
        # DB Update
        db_service.update_followup(
            st.session_state.get("report_id"), 
            res, 
            {"messages": st.session_state["followup_msgs"]}
        )


# ==========================================
# 6) Main UI (Login + Sidebar + App)
# ==========================================
def login_page():
    st.markdown(
        """
        <div class="login-container">
            <h2>🔐 AI Bureau Access</h2>
            <p>공무원 전용 AI 행정관 시스템</p>
        </div>
        """, unsafe_allow_html=True
    )
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        username = st.text_input("아이디(ID)를 입력하세요", placeholder="example: chungju_admin")
        if st.button("로그인", type="primary", use_container_width=True):
            if username:
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.rerun()
            else:
                st.error("아이디를 입력해주세요.")

def main_app():
    # 사이드바 (과거 기록 기능)
    with st.sidebar:
        st.title(f"👤 {st.session_state['username']}님")
        st.caption("충주시청 AI 행정관")
        
        if st.button("➕ 새 업무 시작", use_container_width=True):
            if "workflow_result" in st.session_state:
                del st.session_state["workflow_result"]
            if "followup_msgs" in st.session_state:
                del st.session_state["followup_msgs"]
            st.rerun()
            
        st.markdown("---")
        st.subheader("🗂️ 최근 업무 기록")
        
        # DB에서 내 기록 가져오기
        history = db_service.fetch_history(st.session_state["username"])
        
        if not history:
            st.caption("저장된 기록이 없습니다.")
        else:
            for item in history:
                # 상황 요약해서 버튼명으로
                label = item.get("situation", "제목 없음")[:15] + "..."
                if st.button(f"📄 {label}", key=item['id']):
                    # 선택한 기록 불러오기 (Summary 파싱)
                    try:
                        loaded_res = json.loads(item['summary'])
                        # 호환성 처리
                        loaded_res['situation'] = item.get("situation")
                        st.session_state["workflow_result"] = loaded_res
                        st.session_state["report_id"] = item['id']
                        # 후속대화 복구
                        saved_msgs = loaded_res.get("followup", {}).get("messages", [])
                        st.session_state["followup_msgs"] = saved_msgs
                        st.rerun()
                    except:
                        st.error("기록 불러오기 오류")

    # 메인 화면
    col_left, col_right = st.columns([1, 1.2])

    with col_left:
        st.title("LawBot AI")
        st.markdown("##### 🚀 행정 업무 자동화 에이전트")
        
        user_input = st.text_area("업무 지시 사항", height=150, placeholder="예: 불법주차 과태료 이의신청에 대한 기각 공문을 작성해줘. 증거사진이 명확함.")
        
        if st.button("⚡ 분석 및 공문 생성", type="primary"):
            if user_input:
                with st.spinner("LawBot이 분석 중입니다..."):
                    res = run_workflow(user_input)
                    # DB 저장
                    ins = db_service.insert_initial_report(res, st.session_state["username"])
                    st.session_state["report_id"] = ins.get("id")
                    st.session_state["workflow_result"] = res
                    st.session_state["followup_msgs"] = [] # 새 대화 초기화
            else:
                st.warning("내용을 입력하세요.")

        if "workflow_result" in st.session_state:
            res = st.session_state["workflow_result"]
            st.markdown("---")
            
            with st.expander("📜 법령 및 근거 확인", expanded=False):
                st.markdown(res.get("law", ""))
            
            with st.expander("📰 유사 사례/뉴스", expanded=False):
                st.markdown(res.get("search", ""))

            with st.expander("🧭 처리 방향 (Strategy)", expanded=True):
                st.info(res.get("strategy", ""))

    with col_right:
        if "workflow_result" in st.session_state:
            res = st.session_state["workflow_result"]
            doc = res.get("doc", {})
            meta = res.get("meta", {})
            
            # 공문서 렌더링
            html_content = f"""
            <div class="paper-sheet">
              <div class="stamp">직인생략</div>
              <div class="doc-header">{_escape(doc.get('title', '공 문 서'))}</div>
              <div class="doc-info">
                <span>문서번호: {_escape(meta.get('doc_num',''))}</span>
                <span>시행일자: {_escape(meta.get('today_str',''))}</span>
                <span>수신: {_escape(doc.get('receiver', ''))}</span>
              </div>
              <hr style="border: 1px solid black; margin-bottom: 30px;">
              <div class="doc-body">
            """
            paras = doc.get("body_paragraphs", [])
            if isinstance(paras, str): paras = [paras]
            for p in paras:
                html_content += f"<p style='margin-bottom: 15px;'>{_escape(p)}</p>"
            
            html_content += f"""
              </div>
              <div class="doc-footer">{_escape(doc.get('department_head', '행정기관장'))}</div>
            </div>
            """
            st.markdown(html_content, unsafe_allow_html=True)
            
            st.markdown("---")
            st.subheader("💬 AI 조수와 대화 (수정/문의)")
            render_followup(res)
        else:
             st.markdown(
                """<div style='text-align: center; padding: 150px 0; color: #aaa;'>
                <h3>Document Preview</h3><p>왼쪽에서 업무를 지시하면<br>완성된 공문서가 여기에 나타납니다.</p></div>""",
                unsafe_allow_html=True,
            )

def main():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if not st.session_state["logged_in"]:
        login_page()
    else:
        main_app()

if __name__ == "__main__":
    main()
