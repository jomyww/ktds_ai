
import asyncio
import streamlit as st
import sys
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# 프로젝트 루트 경로 추가 및 환경변수 로드
PROJECT_ROOT = str(Path(__file__).resolve().parents[1])
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
env_path = find_dotenv()
if env_path:
    load_dotenv(env_path, override=True)

# 페이지 설정
st.set_page_config(page_title="Incident IQ MVP", page_icon="🛠️", layout="wide")
from app.rag_pipeline import generate_incident_response

# 스타일 커스텀

st.markdown(
    """
    <style>
      [data-testid="stAppViewContainer"] { font-size: 15px; }
      [data-testid="stMarkdownContainer"] p { font-size: 15px; }
      h1 { font-size: 26px; display: flex; align-items: center; }
      h1 .main-icon { font-size: 36px; margin-right: 10px; vertical-align: middle; }
      h2 { font-size: 18px; display: flex; align-items: center; }
      h2 .section-icon { font-size: 22px; margin-right: 7px; vertical-align: middle; }
      label, .stTextInput label, .stTextArea label { font-size: 15px; }
      .stAlert-success { background: #e0f7fa !important; color: #00695c !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<h1><span class="main-icon">🛠️</span>Incident IQ · 이상징후 대응 에이전트</h1>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 🚀 Incident IQ")
    st.caption("Azure OpenAI + Azure AI Search 기반 에이전트")
    page = st.radio(
        "탭 선택",
        ["이상징후 대응 에이전트", "대시보드", "지식 업로드", "설정"],
        index=0,
        label_visibility="collapsed"
    )
    st.divider()
    st.markdown("**빠른 링크**")
    st.link_button("📘 프로젝트 위키", "https://example.com", disabled=True)
    st.link_button("🧭 운영 가이드", "https://example.com", disabled=True)
    st.caption("링크는 비활성 되어 있으며 추후 오픈 예정입니다.")


symptom = st.text_area("✍️ 오류/이상징후 현상", placeholder="예) 로그인 API 5xx 급증, Kafka broker unreachable ...")
service = st.text_input("🔹서비스명 또는 시스템", placeholder="예) 회원/인증, 결제, 메시징, Kafka 클러스터 등")
extra = st.text_area("🔹추가 정보 (로그, 메트릭, 범위 등)", placeholder="예) 00:42부터 증가, 특정 리전, pod 재시작 반복 등")

btn = st.button("🔎 검색", type="primary")

if btn:
    with st.spinner("분석 중입니다..."):
        result = asyncio.run(generate_incident_response(symptom, service, extra))
    st.success("분석이 완료되었습니다. 아래 결과를 확인하세요.", icon="✅")
    col1, col2 = st.columns([2, 1], gap="large")
    with col1:
        st.markdown('<h2><span class="section-icon">💡</span>조치 가이드 안내</h2>', unsafe_allow_html=True)
        st.markdown(result["answer"])
        if result.get("web_refs"):
            st.info("🔗 인터넷 참고자료")
            for w in result["web_refs"]:
                st.markdown(f"- [{w['name']}]({w['url']}) — {w.get('snippet','')}")
        st.markdown('<h2><span class="section-icon">📑</span>상위 검색 컨텍스트</h2>', unsafe_allow_html=True)
        for h in result["hits"][:5]:
            with st.expander(f"{h['title']} (score={h['score']:.3f})"):
                st.write(h["content"])
                st.caption(f"서비스: {h.get('service','-')} | 심각도: {h.get('severity','-')} | 영향도: {h.get('impact','-')}")
                if h.get("actions"):
                    st.code(h["actions"], language="bash")
    with col2:
        st.markdown('<h2><span class="section-icon">📝</span>공지 포맷 예시</h2>', unsafe_allow_html=True)
        for key in ["suspected", "resolved", "declared", "cleared"]:
            st.code(result["notices"].get(key, ""), language="markdown")
else:
    st.info("검색 조건을 입력 후 **검색** 버튼을 눌러주세요.")
