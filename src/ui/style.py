import streamlit as st

def apply_custom_style():
    st.markdown("""
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
    """, unsafe_allow_html=True)
