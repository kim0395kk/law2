# streamlit_app.py
# -*- coding: utf-8 -*-
"""
Law AI Search (Streamlit) - law.go.kr DRF Open API 기반
- lawSearch.do (목록/검색) + lawService.do (본문)
- "AI 서치" = (상황 텍스트 -> 키워드 확장) -> 본문검색(search=2) + 법령명검색(search=1) -> 디듀프 -> 본문에서 조문 하이라이트
"""

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import requests
import streamlit as st


LAW_SEARCH_URL = "https://www.law.go.kr/DRF/lawSearch.do"
LAW_SERVICE_URL = "https://www.law.go.kr/DRF/lawService.do"

DEFAULT_TIMEOUT = 12


# -----------------------------
# Utilities
# -----------------------------
def _safe_int(x: Any) -> Optional[int]:
    try:
        return int(str(x).strip())
    except Exception:
        return None


def _first_key(d: Dict[str, Any], keys: List[str]) -> Optional[str]:
    lower_map = {k.lower(): k for k in d.keys()}
    for want in keys:
        if want.lower() in lower_map:
            return lower_map[want.lower()]
    return None


def _normalize_space(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _highlight(text: str, terms: List[str]) -> str:
    if not text:
        return text
    out = text
    for t in sorted(set([x for x in terms if x]), key=len, reverse=True):
        # 너무 짧은 토큰은 제외(노이즈 방지)
        if len(t) < 2:
            continue
        out = re.sub(re.escape(t), lambda m: f"**{m.group(0)}**", out, flags=re.IGNORECASE)
    return out


def _extract_terms_from_situation(situation: str, max_terms: int = 8) -> List[str]:
    """
    LLM 없이도 돌아가게 '간단 키워드 추출' (한국어 형태소 분석 없이 휴리스틱)
    - 숫자/기호 제거 후 2~15자 토큰
    - 흔한 불용어 제거
    """
    if not situation:
        return []

    stop = set([
        "있습니다", "합니다", "되었습니다", "대해서", "관련", "검토", "요청", "문의",
        "민원", "처리", "가능", "어떻게", "무엇", "때문", "경우", "그리고", "또한",
        "저희", "우리", "귀하", "사항", "부분", "대한", "해서", "입니다"
    ])

    s = re.sub(r"[^\w\s가-힣]", " ", situation)
    s = _normalize_space(s)
    tokens = [t for t in s.split(" ") if 2 <= len(t) <= 15]
    tokens = [t for t in tokens if t not in stop]
    # 빈도 기반 상위
    freq: Dict[str, int] = {}
    for t in tokens:
        freq[t] = freq.get(t, 0) + 1
    ranked = sorted(freq.items(), key=lambda kv: (-kv[1], -len(kv[0])))
    return [k for k, _ in ranked[:max_terms]]


def _dedupe_by(items: List[Dict[str, Any]], key_candidates: List[str]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for it in items:
        k = None
        for kc in key_candidates:
            if kc in it and it.get(kc) not in (None, "", "0"):
                k = str(it.get(kc))
                break
        if not k:
            k = json.dumps(it, ensure_ascii=False, sort_keys=True)[:120]
        if k in seen:
            continue
        seen.add(k)
        out.append(it)
    return out


# -----------------------------
# Law.go.kr API Client
# -----------------------------
@dataclass
class LawGoClient:
    oc: str

    def _get_json(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        r = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        # law.go.kr은 JSON이더라도 content-type이 애매한 경우가 있어 try/except
        try:
            return r.json()
        except Exception:
            # fallback: text를 json.loads
            return json.loads(r.text)

    def search_laws(
        self,
        query: str,
        search_scope: int = 1,  # 1: 법령명, 2: 본문검색
        page: int = 1,
        display: int = 20,
        sort: str = "efdes",  # 시행일자 내림차순
    ) -> Dict[str, Any]:
        params = {
            "OC": self.oc,
            "target": "law",
            "type": "JSON",
            "query": query,
            "search": search_scope,
            "page": page,
            "display": display,
            "sort": sort,
        }
        return self._get_json(LAW_SEARCH_URL, params)

    def get_law_detail(
        self,
        law_id: Optional[str] = None,
        mst: Optional[str] = None,
        jo: Optional[str] = None,  # 6자리 조번호(옵션)
        lang: str = "KO",
    ) -> Dict[str, Any]:
        params = {
            "OC": self.oc,
            "target": "law",
            "type": "JSON",
            "LANG": lang,
        }
        # ID 또는 MST 중 하나 필수 :contentReference[oaicite:2]{index=2}
        if law_id:
            params["ID"] = law_id
        if mst:
            params["MST"] = mst
        if jo:
            params["JO"] = jo

        return self._get_json(LAW_SERVICE_URL, params)


# -----------------------------
# Parsers (구조가 조금 달라도 최대한 견딤)
# -----------------------------
def parse_search_results(payload: Dict[str, Any]) -> Tuple[int, List[Dict[str, Any]]]:
    """
    lawSearch 결과에서 totalCnt + law 리스트를 최대한 안전하게 추출
    가이드의 응답 필드: totalCnt, law(반복) 등 :contentReference[oaicite:3]{index=3}
    """
    if not isinstance(payload, dict):
        return 0, []

    root = payload
    # 보통 최상위에 LawSearch 또는 searchResult 같은 키가 한 번 감싸는 경우가 있음
    if len(root) == 1 and isinstance(next(iter(root.values())), dict):
        root = next(iter(root.values()))

    total = 0
    for k in ["totalCnt", "TotalCnt", "total_count"]:
        if k in root:
            total = _safe_int(root.get(k)) or 0
            break

    # law 리스트 추출
    law_key = _first_key(root, ["law", "Law", "laws"])
    laws = root.get(law_key, []) if law_key else []
    if isinstance(laws, dict):
        laws = [laws]
    if not isinstance(laws, list):
        laws = []

    # 표준화(필드명이 한글인 경우도 있어서 "있는 그대로" 유지 + 자주 쓰는 키만 매핑)
    norm: List[Dict[str, Any]] = []
    for it in laws:
        if not isinstance(it, dict):
            continue
        norm.append(it)
    return total, norm


def extract_articles_from_detail(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    lawService 상세(JSON)에서 '조문내용'이 있는 객체들을 전부 수집
    가이드 응답 필드에 '조문내용/조문번호/조문제목' 등이 있음 :contentReference[oaicite:4]{index=4}
    """
    articles: List[Dict[str, Any]] = []

    def walk(x: Any):
        if isinstance(x, dict):
            if "조문내용" in x:
                articles.append(x)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(payload)
    return articles


def pick_law_meta(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    상세 결과에서 메타(법령명/시행일/소관부처 등) 후보 키를 대충 긁어옴.
    """
    meta = {}

    def find_first(d: Dict[str, Any], candidates: List[str]) -> Optional[Any]:
        for c in candidates:
            if c in d and d[c] not in (None, "", "0"):
                return d[c]
        return None

    # 전체를 훑어 가장 먼저 만나는 메타 키들 수집
    def walk(d: Any):
        if not isinstance(d, dict):
            return
        for key, val in d.items():
            if key in ["법령명_한글", "법령명한글", "법령명", "법령명약칭", "소관부처", "소관부처명", "시행일자", "공포일자", "공포번호", "법령ID"]:
                if key not in meta and val not in (None, "", "0"):
                    meta[key] = val
        for v in d.values():
            if isinstance(v, dict):
                walk(v)

    walk(payload)

    # 보기 좋은 별칭
    meta_view = {
        "법령명": find_first(meta, ["법령명_한글", "법령명한글", "법령명"]),
        "시행일자": find_first(meta, ["시행일자"]),
        "공포일자": find_first(meta, ["공포일자"]),
        "공포번호": find_first(meta, ["공포번호"]),
        "소관부처": find_first(meta, ["소관부처", "소관부처명"]),
        "법령ID": find_first(meta, ["법령ID"]),
    }
    return {k: v for k, v in meta_view.items() if v not in (None, "", "0")}


# -----------------------------
# Streamlit App
# -----------------------------
st.set_page_config(page_title="법령 AI 서치 (law.go.kr API)", page_icon="⚖️", layout="wide")

st.title("⚖️ 법령 AI 서치 (국가법령정보 Open API)")
st.caption("※ 민감정보(성명/주소/연락처/차량번호 등) 입력 금지. 결과는 참고용 초안입니다.")

# Sidebar: Secrets
with st.sidebar:
    st.header("설정")
    oc = st.secrets.get("LAWGO_OC", "") if hasattr(st, "secrets") else ""
    oc = st.text_input("LAWGO_OC (법령 Open API OC)", value=oc, type="password", help="law.go.kr Open API 인증값(OC).")
    if not oc:
        st.warning("OC가 비어있으면 검색이 동작하지 않습니다.")

    mode = st.radio(
        "검색 모드",
        ["AI 서치(상황→키워드 확장)", "키워드 직접검색"],
        index=0,
    )

    search_scope = st.selectbox(
        "검색 범위",
        options=[("법령명(빠름)", 1), ("본문검색(강함)", 2)],
        index=1,
        format_func=lambda x: x[0],
    )[1]

    display = st.slider("결과 개수", 10, 100, 30, 10)
    sort = st.selectbox(
        "정렬",
        options=[
            ("시행일 내림차순(추천)", "efdes"),
            ("시행일 오름차순", "efasc"),
            ("공포일 내림차순", "ddes"),
            ("공포일 오름차순", "dasc"),
            ("법령명 오름차순", "lasc"),
            ("법령명 내림차순", "ldes"),
        ],
        index=0,
    )[1]

    advanced = st.checkbox("고급: 원본 JSON 보기(디버그)", value=False)


if not oc:
    st.stop()

client = LawGoClient(oc=oc)


@st.cache_data(ttl=3600, show_spinner=False)
def cached_search(query: str, search_scope: int, page: int, display: int, sort: str) -> Dict[str, Any]:
    return client.search_laws(query=query, search_scope=search_scope, page=page, display=display, sort=sort)


@st.cache_data(ttl=3600, show_spinner=False)
def cached_detail(law_id: Optional[str], mst: Optional[str]) -> Dict[str, Any]:
    return client.get_law_detail(law_id=law_id, mst=mst, lang="KO")


# Input
colL, colR = st.columns([1.2, 1])
with colL:
    if mode.startswith("AI"):
        situation = st.text_area(
            "상황/질문을 넣으면, 키워드를 뽑아서 법령을 찾아줍니다.",
            height=140,
            placeholder="예: 무단방치 차량 강제처리 절차와 근거조문, 통지/공시송달 방식까지 정리 필요",
        )
        manual_terms = st.text_input("추가 키워드(선택, 쉼표로 구분)", value="")
    else:
        situation = ""
        query_direct = st.text_input("검색어(법령명/키워드)", value="", placeholder="예: 자동차관리법, 무단방치, 공시송달")

with colR:
    st.markdown("### 사용 팁")
    st.markdown(
        "- **본문검색(강함)**은 결과가 풍부하지만 느릴 수 있어요.\n"
        "- 결과에서 법령을 클릭하면 **조문 단위로 하이라이트**합니다.\n"
        "- 법령 상세는 `lawService.do?target=law`로 가져옵니다. :contentReference[oaicite:5]{index=5}"
    )

run = st.button("🔎 검색 실행", use_container_width=True)

if run:
    try:
        if mode.startswith("AI"):
            base_terms = _extract_terms_from_situation(situation, max_terms=8)
            extra = [t.strip() for t in manual_terms.split(",") if t.strip()]
            terms = _dedupe_by([{"t": x} for x in (base_terms + extra)], ["t"])
            terms = [x["t"] for x in terms][:10]

            if not terms:
                st.warning("키워드를 추출하지 못했습니다. 텍스트를 조금 더 구체적으로 적거나, 추가 키워드를 넣어주세요.")
                st.stop()

            st.write("**추출/사용 키워드:** ", ", ".join(terms))

            # 키워드별 검색(페이지 1 고정)
            all_items: List[Dict[str, Any]] = []
            for t in terms:
                payload = cached_search(query=t, search_scope=search_scope, page=1, display=display, sort=sort)
                _, items = parse_search_results(payload)
                for it in items:
                    it["_hit_term"] = t
                all_items.extend(items)

            # 디듀프(법령ID/법령일련번호/현행연혁코드 등 후보로)
            results = _dedupe_by(all_items, ["법령ID", "법령일련번호", "현행연혁코드", "법령상세링크"])

        else:
            if not query_direct.strip():
                st.warning("검색어를 입력하세요.")
                st.stop()
            payload = cached_search(query=query_direct.strip(), search_scope=search_scope, page=1, display=display, sort=sort)
            _, items = parse_search_results(payload)
            results = items

        if advanced:
            st.subheader("원본 검색 JSON(디버그)")
            st.json(payload if not mode.startswith("AI") else {"items_count": len(results), "sample": results[:3]})

        if not results:
            st.info("검색 결과가 없습니다.")
            st.stop()

        # 보기 좋게 표준 컬럼 뽑기 (가이드에 있는 필드들 중심) :contentReference[oaicite:6]{index=6}
        view_rows = []
        for i, it in enumerate(results, start=1):
            view_rows.append({
                "No": i,
                "법령명": it.get("법령명한글") or it.get("법령명_한글") or it.get("법령명") or it.get("법령약칭명") or "",
                "시행일자": it.get("시행일자") or "",
                "공포일자": it.get("공포일자") or "",
                "소관부처": it.get("소관부처명") or it.get("소관부처") or "",
                "법령ID": it.get("법령ID") or "",
                "법령일련번호": it.get("법령일련번호") or it.get("MST") or "",
                "_hit": it.get("_hit_term", ""),
            })

        st.subheader("검색 결과")
        st.dataframe(view_rows, use_container_width=True, hide_index=True)

        # 선택
        options = [
            f"{r['No']:>02}. {r['법령명']} (시행 {r['시행일자']})"
            for r in view_rows
        ]
        pick = st.selectbox("법령 선택", options=options, index=0)
        pick_no = int(pick.split(".")[0].strip())
        picked = view_rows[pick_no - 1]

        law_id = str(picked.get("법령ID") or "").strip() or None
        mst = str(picked.get("법령일련번호") or "").strip() or None

        st.divider()
        st.subheader("법령 본문/조문")
        detail = cached_detail(law_id=law_id, mst=mst)

        if advanced:
            st.subheader("원본 상세 JSON(디버그)")
            st.json(detail)

        meta = pick_law_meta(detail)
        if meta:
            st.markdown("#### 메타")
            st.write(meta)

        articles = extract_articles_from_detail(detail)
        if not articles:
            st.warning("상세 JSON에서 '조문내용'을 찾지 못했습니다. (디버그 JSON을 켜고 구조를 확인해보세요.)")
            st.stop()

        # 하이라이트 기준 단어
        if mode.startswith("AI"):
            hl_terms = _extract_terms_from_situation(situation, max_terms=12)
            hl_terms += [picked.get("_hit", "")] if picked.get("_hit") else []
            hl_terms = [t for t in hl_terms if t]
        else:
            hl_terms = [query_direct.strip()]

        # 조문 필터
        filter_word = st.text_input("조문 필터(선택: 이 단어가 포함된 조문만 보기)", value="")
        shown = 0

        for a in articles:
            title = a.get("조문제목") or ""
            no = a.get("조문번호")
            no2 = a.get("조문가지번호")
            label = "조문"
            if no is not None:
                label = f"제{no}조" if _safe_int(no) is not None else f"{no}"
                if no2 and str(no2) not in ("0", "", "None"):
                    label += f"의{no2}"

            body = a.get("조문내용") or ""
            plain = _normalize_space(re.sub(r"<[^>]+>", " ", str(body)))  # 혹시 HTML이 섞이면 제거

            if filter_word and (filter_word not in plain) and (filter_word not in title):
                continue

            # 하이라이트
            md = _highlight(plain, hl_terms)

            with st.expander(f"{label} {title}".strip(), expanded=False):
                st.markdown(md)

            shown += 1
            if shown >= 80:
                st.info("조문이 많아 80개까지만 표시했습니다. (필터를 사용하세요)")
                break

        st.caption("목록 API: lawSearch.do?target=law :contentReference[oaicite:7]{index=7}  |  본문 API: lawService.do?target=law :contentReference[oaicite:8]{index=8}")

    except requests.HTTPError as e:
        st.error(f"HTTP 오류: {e}")
    except Exception as e:
        st.error(f"오류: {e}")
