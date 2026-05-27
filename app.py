import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
import os
import re
import html
from datetime import datetime
from openai import OpenAI

try:
    import plotly.graph_objects as go
except Exception:
    go = None

# =========================
# 기본 설정
# =========================

st.set_page_config(
    page_title="Counsel Insight AI",
    page_icon="🧠",
    layout="wide"
)

DATA_FILE = "counsel_results.csv"

# Streamlit Cloud 배포 시 Secrets에 OPENAI_API_KEY 등록 필요
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# 개발자 모드: Streamlit Secrets 또는 환경변수로 제어
DEV_MODE = str(st.secrets.get("DEV_MODE", os.environ.get("DEV_MODE", "false"))).lower() in ["true", "1", "yes", "y"]

# 관리자 모드 기본값
if "admin_mode" not in st.session_state:
    st.session_state["admin_mode"] = False


# =========================
# 샘플 상담 데이터 3개
# =========================

SAMPLE_DATA = {
    "샘플 1 - 진로·성적 불안": {
        "student_id": "U-0001",
        "grade": "중학교 3학년",
        "referral_source": "담임 관찰",
        "topic": "진로·학업",
        "observation": "최근 수업 시간에 멍하니 있는 시간이 늘었고, 쉬는 시간에도 친구들과 잘 어울리지 않고 혼자 앉아 있는 모습이 자주 관찰됨. 수행평가 제출은 하고 있으나 완성도가 떨어지고, 시험 이야기가 나오면 표정이 굳어짐.",
        "student_statement": "고등학교도 정해야 하고 성적도 올려야 하는데 뭘 먼저 해야 할지 모르겠어요. 부모님은 제가 좋은 학교에 가길 바라시는데 저는 자신이 없어요. 요즘은 공부하려고 앉아도 계속 걱정만 나요.",
        "risk_check": "없음",
        "teacher_memo": "진로와 성적에 대한 부담이 큰 것으로 보임. 즉각적인 위기 신호는 없으나 불안이 학습 집중에 영향을 주는 것으로 판단됨."
    },
    "샘플 2 - 스마트폰 과의존": {
        "student_id": "U-0002",
        "grade": "초등학교 6학년",
        "referral_source": "학부모 요청",
        "topic": "생활습관·스마트폰 사용",
        "observation": "최근 아침 등교 시 자주 피곤해 보이고, 수업 중 졸거나 집중하지 못하는 모습이 관찰됨. 쉬는 시간에는 친구들과 놀기보다 스마트폰 게임 이야기만 주로 함. 과제 제출이 늦어지는 경우가 늘어남.",
        "student_statement": "밤에 게임을 조금만 하려고 했는데 하다 보면 시간이 금방 가요. 친구들이랑 같이 하는 게임이라 저만 나가기가 좀 그래요. 엄마가 하지 말라고 하면 더 짜증 나고, 공부는 재미가 없어요.",
        "risk_check": "없음",
        "teacher_memo": "스마트폰 사용 자체를 비난하기보다 사용 시간과 상황을 스스로 인식하도록 돕는 접근이 필요함. 수면 부족과 과제 지연이 함께 나타남."
    },
    "샘플 3 - 등교곤란·고립 경향": {
        "student_id": "U-0003",
        "grade": "고등학교 1학년",
        "referral_source": "담임 관찰 및 보호자 상담",
        "topic": "등교곤란·대인관계 회피",
        "observation": "최근 3주간 지각과 결석이 반복되고 있음. 등교한 날에도 교실 뒤쪽에 혼자 앉아 있으며, 조별활동이나 발표 상황에서 강한 거부감을 보임. 점심시간에는 식사를 거르거나 혼자 있는 경우가 많음.",
        "student_statement": "학교에 오면 사람들이 저를 보는 것 같고, 말 걸기도 싫어요. 집에 있으면 마음이 좀 편한데 학교에 오려고 하면 아침부터 배가 아파요. 친구들이 싫은 건 아닌데 그냥 아무하고도 말하고 싶지 않아요.",
        "risk_check": "자해·자살 직접 언급 없음, 학대 의심 없음, 학교폭력 피해 여부 추가 확인 필요",
        "teacher_memo": "등교 부담과 대인회피가 함께 나타남. 고립 경향이 장기화되지 않도록 낮은 압박의 상담관계 형성이 필요함. 보호자와의 협력 및 전문상담교사 연계 검토 필요."
    }
}


# =========================
# 학생 유형 매뉴얼 데이터
# =========================

TYPE_MANUAL = {
    "T01 친구관계 어려움형": {
        "특징": "친구에게 다가가기 어렵거나 거절을 두려워하고, 소외감이나 관계 갈등을 경험하는 유형",
        "상담목표": "관계 상황을 안전하게 이야기하고, 작은 관계 시도를 정한다.",
        "교사질문": [
            "요즘 친구들과 있을 때 가장 불편한 순간은 언제야?",
            "편하게 말할 수 있는 친구가 한 명이라도 있을까?",
            "이번 주에 해볼 수 있는 작은 관계 행동은 뭐가 있을까?"
        ],
        "피드백": "네가 관계에서 힘들었던 점을 말로 표현한 것 자체가 중요한 시작이야."
    },
    "T02 불안·걱정형": {
        "특징": "성적, 진로, 부모 기대, 미래에 대한 걱정이 많고 생각이 많아지는 유형",
        "상담목표": "걱정을 구체화하고, 통제 가능한 일부터 작은 계획을 세운다.",
        "교사질문": [
            "지금 가장 크게 걱정되는 건 뭐야?",
            "그중에서 네가 바꿀 수 있는 부분은 어떤 게 있을까?",
            "오늘 당장 할 수 있는 가장 작은 행동 하나는 뭐가 좋을까?"
        ],
        "피드백": "지금 모든 걸 한 번에 해결하지 않아도 괜찮아. 하나씩 정리해보면 돼."
    },
    "T03 무기력·우울형": {
        "특징": "의욕 저하, 활동 감소, 자기비난, 피로감, 흥미 저하가 나타나는 유형",
        "상담목표": "감정을 표현하고 생활리듬을 회복하며 도움 요청 가능성을 확인한다.",
        "교사질문": [
            "요즘 하루 중 가장 힘든 시간은 언제야?",
            "예전보다 줄어든 활동이 있다면 뭐가 있을까?",
            "오늘 할 수 있는 아주 작은 일 하나만 정하면 뭐가 좋을까?"
        ],
        "피드백": "큰 변화를 바로 만들지 않아도 돼. 작은 행동 하나를 해낸 것도 의미 있어."
    },
    "T04 분노·공격형": {
        "특징": "화를 자주 내거나 말다툼, 충동적 반응, 공격적 표현이 나타나는 유형",
        "상담목표": "감정과 행동을 분리해서 보고, 분노 상황에서 대체 행동을 찾는다.",
        "교사질문": [
            "그때 가장 화가 났던 이유는 뭐였어?",
            "화가 나기 직전에 몸이나 생각에서 어떤 신호가 있었어?",
            "다음에 비슷한 상황이 오면 어떤 방식으로 멈춰볼 수 있을까?"
        ],
        "피드백": "화가 난 감정은 이해할 수 있어. 다만 그 감정을 어떻게 표현할지는 같이 연습할 수 있어."
    },
    "T05 산만·충동형": {
        "특징": "집중 유지가 어렵고 즉흥적으로 행동하거나 계획 실천이 어려운 유형",
        "상담목표": "한 번에 하나의 목표를 정하고 짧은 체크리스트로 실천을 돕는다.",
        "교사질문": [
            "수업 중 가장 집중이 끊기는 순간은 언제야?",
            "오늘 해야 할 일 중 하나만 고르면 뭐가 제일 중요할까?",
            "알림이나 체크표가 있으면 도움이 될까?"
        ],
        "피드백": "한 번에 다 바꾸려고 하지 말고, 오늘 할 일 하나부터 성공해보자."
    },
    "T06 스마트폰·인터넷 과의존형": {
        "특징": "게임, 유튜브, SNS 사용 시간이 늘고 수면, 학습, 과제에 영향을 받는 유형",
        "상담목표": "사용 패턴을 인식하고, 대체활동과 사용 조절 방법을 찾는다.",
        "교사질문": [
            "스마트폰을 가장 많이 사용하게 되는 시간은 언제야?",
            "사용을 멈추기 어려운 이유는 뭐라고 생각해?",
            "줄이는 대신 해볼 수 있는 활동이 하나 있다면 뭐가 좋을까?"
        ],
        "피드백": "스마트폰을 무조건 나쁘게 볼 필요는 없어. 다만 네 생활을 방해하지 않게 조절하는 연습이 필요해."
    },
    "T07 규칙 미준수형": {
        "특징": "지각, 과제 미제출, 교칙 위반 등 규칙을 반복적으로 지키기 어려운 유형",
        "상담목표": "규칙 위반의 원인을 파악하고 실천 가능한 약속을 정한다.",
        "교사질문": [
            "규칙을 지키기 어려운 순간은 주로 언제야?",
            "그때 너를 방해하는 이유가 있다면 뭐야?",
            "이번 주에 지킬 수 있는 현실적인 약속 하나는 뭐가 좋을까?"
        ],
        "피드백": "규칙을 지키는 건 혼내기 위한 게 아니라 네 생활을 안정시키기 위한 거야."
    },
    "T08 등교곤란·학업중단 위험형": {
        "특징": "지각, 결석, 학교 회피, 자퇴 고민 등이 나타나는 유형",
        "상담목표": "등교 부담 요인을 찾고 학교 내 안전한 지지자와 공간을 연결한다.",
        "교사질문": [
            "학교에 오기 가장 힘든 순간은 언제부터 시작돼?",
            "학교에서 조금이라도 편한 장소나 사람이 있을까?",
            "이번 주에 가능한 가장 낮은 등교 목표는 뭐가 좋을까?"
        ],
        "피드백": "학교에 오기 힘든 이유를 말해준 것만으로도 중요한 시작이야."
    },
    "T09 고립·은둔형": {
        "특징": "대인접촉을 피하고 외부활동이 줄며, 방이나 집 안에 머무는 시간이 늘어난 유형",
        "상담목표": "낮은 압박으로 신뢰관계를 형성하고 일상 회복의 작은 단계를 만든다.",
        "교사질문": [
            "요즘 하루 중 가장 편한 시간은 언제야?",
            "사람을 만나는 것 중 가장 부담되는 부분은 뭐야?",
            "방 밖이나 집 밖에서 아주 짧게 해볼 수 있는 일이 있을까?"
        ],
        "피드백": "빠르게 바뀌지 않아도 괜찮아. 지금은 안전하게 연결되는 것부터가 중요해."
    },
    "T10 위기신호형": {
        "특징": "자해, 자살 언급, 학대 의심, 심각한 폭력 피해 등 즉시 개입이 필요한 유형",
        "상담목표": "학생 안전을 우선 확보하고 보호자, 전문상담교사, 전문기관과 즉시 연계한다.",
        "교사질문": [
            "지금 혼자 있니?",
            "지금 바로 도움을 받을 수 있는 어른이 주변에 있니?",
            "안전을 위해 선생님이 바로 함께 도움을 연결해도 괜찮을까?"
        ],
        "피드백": "이 이야기는 혼자 견디게 두지 않을 거야. 지금은 네 안전이 가장 중요해."
    }
}


# =========================
# 학생 페르소나 응답 규칙
# =========================

PERSONA_RULES = {
    "T01 친구관계 어려움형": [
        "친구 관계에 대해 조심스럽게 말한다.",
        "거절당할까 봐 걱정하는 표현을 사용한다.",
        "처음부터 구체적인 갈등을 모두 말하지 않고 조금씩 드러낸다."
    ],
    "T02 불안·걱정형": [
        "말줄임표(...)를 자연스럽게 사용한다.",
        "잘 모르겠어요, 걱정돼요, 자신이 없어요 같은 표현을 사용한다.",
        "확신 없는 짧은 답변을 자주 사용한다."
    ],
    "T03 무기력·우울형": [
        "답변이 짧고 에너지가 낮다.",
        "그냥요, 별로 하고 싶은 게 없어요 같은 표현을 사용한다.",
        "자기비난 표현이 가끔 나타나지만 과도하게 극단적으로 묘사하지 않는다."
    ],
    "T04 분노·공격형": [
        "방어적이고 예민한 말투를 보인다.",
        "교사의 질문에 왜요?, 그게 제 잘못이에요?처럼 반응할 수 있다.",
        "욕설이나 과도한 공격 표현은 사용하지 않는다."
    ],
    "T05 산만·충동형": [
        "답변 주제가 조금씩 바뀔 수 있다.",
        "집중이 오래 유지되지 않는다.",
        "짧고 즉흥적인 답변을 사용한다."
    ],
    "T06 스마트폰·인터넷 과의존형": [
        "스마트폰 사용을 정당화하는 표현을 사용한다.",
        "친구 관계나 게임 보상에 대한 언급을 포함한다.",
        "사용 조절에 대해 하고 싶지만 어렵다는 양가감정을 표현한다."
    ],
    "T07 규칙 미준수형": [
        "규칙을 지키기 어려운 이유를 외부 상황 탓으로 말할 수 있다.",
        "약속에 대해 부담을 느낀다.",
        "단순 훈계에는 방어적으로 반응한다."
    ],
    "T08 등교곤란·학업중단 위험형": [
        "학교에 오는 것 자체에 부담을 표현한다.",
        "배가 아프다, 아침에 힘들다 같은 신체화 표현이 가능하다.",
        "낮은 목표에는 조금 반응한다."
    ],
    "T09 고립·은둔형": [
        "말수가 적고 관계 질문을 부담스러워한다.",
        "혼자 있는 게 편해요 같은 표현을 사용한다.",
        "갑자기 적극적으로 변하지 않는다."
    ],
    "T10 위기신호형": [
        "직접적이고 자극적인 표현은 피하되 위험 신호를 암시할 수 있다.",
        "교사가 안전 확인을 하도록 유도되는 단서를 포함할 수 있다.",
        "학생 안전과 전문기관 연계가 필요한 상황으로 이어질 수 있음을 간접적으로 드러낸다."
    ]
}


# =========================
# CSS 디자인
# =========================

st.markdown("""
<style>
/* =========================
   Clean Green Theme
   - 학생 상담 카카오톡 인터페이스는 아래 kakao-* 스타일 그대로 유지
   ========================= */
:root {
    --main-green: #2F9364;
    --deep-green: #1F6F4B;
    --soft-green: #EAF5EF;
    --pale-green: #F4FAF7;
    --ink: #111111;
    --text: #1F2937;
    --muted: #5B6573;
    --line: #E5E7EB;
    --white: #FFFFFF;
}

/* 전체 배경 */
.stApp {
    background: #FFFFFF;
    color: var(--text);
}
.main {
    background-color: #FFFFFF;
}
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 3rem;
    max-width: 1280px;
}

/* 상단 타이틀 박스 */
.title-box {
    background: #FFFFFF;
    padding: 34px 36px 30px 36px;
    border-radius: 22px;
    color: var(--ink);
    margin-bottom: 18px;
    border: 1px solid #E7ECE9;
    border-left: 12px solid var(--main-green);
    box-shadow: 0 8px 28px rgba(17, 17, 17, 0.06);
    position: relative;
    overflow: hidden;
}
.title-box::after {
    content: "";
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    height: 8px;
    background: var(--main-green);
}
.title-box h1 {
    color: var(--ink) !important;
    font-weight: 900;
    letter-spacing: -0.04em;
    margin-bottom: 8px;
}
.title-box p {
    color: var(--main-green) !important;
    font-size: 1.05rem;
    font-weight: 700;
    margin: 0;
}

/* 경고/안내 박스 */
.notice-box {
    background-color: var(--pale-green);
    border: 1px solid #BBDCCB;
    border-left: 6px solid var(--main-green);
    color: #174A34;
    padding: 15px 18px;
    border-radius: 14px;
    margin-bottom: 18px;
    font-weight: 600;
}

/* 시작하기 카드 */
.small-guide {
    background-color: #FFFFFF;
    color: var(--text);
    padding: 24px;
    border-radius: 20px;
    border: 1px solid #DDE8E2;
    min-height: 160px;
    box-shadow: 0 6px 18px rgba(31, 111, 75, 0.08);
    transition: transform .15s ease, box-shadow .15s ease, border .15s ease;
}
.small-guide:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 26px rgba(31, 111, 75, 0.14);
    border-color: #A7D1BB;
}
.small-guide h3 {
    color: var(--ink) !important;
    margin-top: 0;
    margin-bottom: 10px;
    font-weight: 900;
    letter-spacing: -0.03em;
}
.small-guide p {
    color: #374151 !important;
    line-height: 1.65;
    font-size: 0.98rem;
}
.small-guide b {
    color: #FFFFFF !important;
    background-color: var(--main-green);
    padding: 7px 12px;
    border-radius: 999px;
    font-size: 0.86rem;
}

/* 탭: 초록 포인트 */
button[data-baseweb="tab"] {
    color: #4B5563;
    font-weight: 700;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: var(--main-green) !important;
    border-bottom-color: var(--main-green) !important;
}

/* 주요 버튼 */
.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"] {
    background-color: var(--main-green) !important;
    border-color: var(--main-green) !important;
    color: white !important;
    font-weight: 800;
    border-radius: 12px;
}
.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="baseButton-primary"]:hover {
    background-color: var(--deep-green) !important;
    border-color: var(--deep-green) !important;
}
.stButton > button {
    border-radius: 12px;
    border-color: #CFE2D8;
}

/* 메트릭/카드 느낌 정리 */
div[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #E1EAE5;
    border-radius: 16px;
    padding: 14px 16px;
    box-shadow: 0 4px 14px rgba(17, 17, 17, 0.04);
}
div[data-testid="stMetricLabel"] {
    color: #5B6573;
}
div[data-testid="stMetricValue"] {
    color: var(--ink);
    font-weight: 900;
}

/* 기본 info/success/warning 박스 톤을 과하게 튀지 않게 */
div[data-testid="stAlert"] {
    border-radius: 14px;
}

/* 입력창 포커스 */
input:focus, textarea:focus {
    border-color: var(--main-green) !important;
    box-shadow: 0 0 0 1px var(--main-green) !important;
}

/* 사이드바 */
section[data-testid="stSidebar"] {
    background: #F7FBF8;
    border-right: 1px solid #E1EAE5;
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: var(--ink);
}

/* 데이터프레임/구분선 */
hr {
    border-color: #E1EAE5;
}



/* =========================
   Light UI hard override
   Streamlit Cloud/브라우저 다크 테마에서도 글자와 입력창이 명확히 보이도록 보정
   ========================= */
html, body, .stApp, [data-testid="stAppViewContainer"] {
    background-color: #FFFFFF !important;
    color: var(--text) !important;
}

/* 일반 텍스트/라벨: 흰 배경에서 반드시 진한 글자 */
.stApp,
.stApp p,
.stApp span,
.stApp label,
.stApp div,
.stApp li,
.stApp h1,
.stApp h2,
.stApp h3,
.stApp h4,
.stApp h5,
.stApp h6,
[data-testid="stMarkdownContainer"],
[data-testid="stWidgetLabel"],
[data-testid="stWidgetLabel"] p,
[data-testid="stText"],
[data-testid="stCaptionContainer"] {
    color: var(--text) !important;
}

/* 타이틀/공지 박스 내부는 지정 색 유지 */
.title-box, .title-box *,
.notice-box, .notice-box *,
.small-guide, .small-guide *,
.kakao-chat-wrap, .kakao-chat-wrap *,
.chat-section-title,
.chat-input-guide, .chat-input-guide * {
    color: inherit;
}
.title-box h1 { color: var(--ink) !important; }
.title-box p { color: var(--main-green) !important; }
.notice-box { color: #174A34 !important; }
.small-guide h3 { color: var(--ink) !important; }
.small-guide p { color: #374151 !important; }
.small-guide b { color: #FFFFFF !important; }
.chat-section-title { color: #FFFFFF !important; }
.chat-input-guide { color: #7C2D12 !important; }

/* 입력창/선택창/텍스트영역: 어두운 기본 테마 제거 */
.stTextInput input,
.stTextArea textarea,
.stNumberInput input,
.stDateInput input,
.stTimeInput input,
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea,
[data-baseweb="select"] > div,
[data-baseweb="select"] input {
    background-color: #FFFFFF !important;
    color: #111827 !important;
    border-color: #CFE2D8 !important;
    caret-color: var(--main-green) !important;
}

/* Selectbox 내부 글자/아이콘 */
[data-baseweb="select"] span,
[data-baseweb="select"] div,
[data-baseweb="select"] svg {
    color: #111827 !important;
    fill: #111827 !important;
}

/* 드롭다운 메뉴 */
ul[role="listbox"],
li[role="option"],
[data-baseweb="popover"] div {
    background-color: #FFFFFF !important;
    color: #111827 !important;
}
li[role="option"]:hover,
li[aria-selected="true"] {
    background-color: var(--soft-green) !important;
    color: #111827 !important;
}

/* placeholder가 흰색처럼 보이지 않게 */
.stTextInput input::placeholder,
.stTextArea textarea::placeholder,
[data-baseweb="input"] input::placeholder,
[data-baseweb="textarea"] textarea::placeholder {
    color: #6B7280 !important;
    opacity: 1 !important;
}

/* disabled/비활성 입력도 읽히게 */
input:disabled,
textarea:disabled,
button:disabled,
[aria-disabled="true"] {
    opacity: 0.65 !important;
}

/* 체크박스/라디오 글자 */
.stCheckbox label,
.stCheckbox p,
.stRadio label,
.stRadio p {
    color: #111827 !important;
}

/* 일반 버튼: 흰 배경 + 초록 테두리로 정리 */
.stButton > button:not([kind="primary"]):not([data-testid="baseButton-primary"]) {
    background-color: #FFFFFF !important;
    color: #174A34 !important;
    border: 1px solid #BBDCCB !important;
    font-weight: 700;
}
.stButton > button:not([kind="primary"]):not([data-testid="baseButton-primary"]):hover {
    background-color: var(--soft-green) !important;
    color: #0F5132 !important;
    border-color: var(--main-green) !important;
}

/* 사이드바: 드래그/다크테마 영향 최소화 */
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] * {
    color: #111827 !important;
}
section[data-testid="stSidebar"] .stAlert,
section[data-testid="stSidebar"] .stAlert * {
    color: #174A34 !important;
}
section[data-testid="stSidebar"] input {
    background-color: #FFFFFF !important;
    color: #111827 !important;
    border-color: #CFE2D8 !important;
}

/* Alert 박스 안 텍스트가 흰색으로 보이는 문제 방지 */
div[data-testid="stAlert"] * {
    color: #174A34 !important;
}

/* 데이터프레임/표 텍스트 */
[data-testid="stDataFrame"],
[data-testid="stDataFrame"] * {
    color: #111827 !important;
}

/* 사용자가 드래그 선택했을 때도 대비 확보 */
::selection {
    background: #CFEAD9;
    color: #111827;
}
::-moz-selection {
    background: #CFEAD9;
    color: #111827;
}

/* =========================
   Kakao-style chat UI
   학생 상담 인터페이스는 기존 색상 유지
   ========================= */
.kakao-chat-wrap {
    background-color: #B8C9D6;
    border-radius: 18px;
    padding: 24px;
    min-height: 420px;
    max-height: 620px;
    overflow-y: auto;
    border: 1px solid #9FB2C0;
    margin-top: 16px;
    margin-bottom: 16px;
}

.kakao-row {
    display: flex;
    margin-bottom: 16px;
    align-items: flex-start;
}

.kakao-row.student {
    justify-content: flex-start;
}

.kakao-row.teacher {
    justify-content: flex-end;
}

.kakao-avatar {
    width: 38px;
    height: 38px;
    border-radius: 50%;
    background: #8DD3E5;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-right: 10px;
    font-size: 20px;
    flex-shrink: 0;
}

.kakao-message-block {
    max-width: 72%;
}

.kakao-name {
    font-size: 13px;
    color: #263238;
    margin-bottom: 4px;
    font-weight: 600;
}

.kakao-bubble {
    padding: 12px 15px;
    border-radius: 16px;
    font-size: 16px;
    line-height: 1.55;
    color: #111827;
    word-break: keep-all;
    white-space: pre-wrap;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}

.kakao-bubble.student {
    background-color: #FFFFFF;
    border-top-left-radius: 4px;
}

.kakao-bubble.teacher {
    background-color: #FEE500;
    border-top-right-radius: 4px;
}

.kakao-time {
    font-size: 11px;
    color: #455A64;
    margin-top: 4px;
}

.kakao-time.teacher {
    text-align: right;
}

.chat-section-title {
    background-color: #1F2937;
    color: white;
    padding: 12px 16px;
    border-radius: 12px;
    margin-top: 18px;
    margin-bottom: 8px;
    font-weight: 700;
}

.chat-input-guide {
    background-color: #FFF7ED;
    color: #7C2D12;
    border: 1px solid #FDBA74;
    padding: 10px 14px;
    border-radius: 10px;
    margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)


# =========================
# 공통 함수
# =========================

def analyze_with_openai(prompt, use_file_search=True):
    """
    OpenAI API 호출 함수
    use_file_search=True이면 업로드한 상담 자료(Vector Store)를 검색해서 답변에 활용함
    """
    try:
        if use_file_search and "VECTOR_STORE_ID" in st.secrets:
            response = client.responses.create(
                model="gpt-4.1-mini",
                input=prompt,
                tools=[
                    {
                        "type": "file_search",
                        "vector_store_ids": [st.secrets["VECTOR_STORE_ID"]],
                        "max_num_results": 5
                    }
                ]
            )
        else:
            response = client.responses.create(
                model="gpt-4.1-mini",
                input=prompt
            )

        return response.output_text

    except Exception as e:
        raise Exception(f"OpenAI API 호출 중 오류가 발생했습니다: {e}")


def extract_json_text(text):
    if not text:
        return ""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    match = re.search(r"\{.*\}", stripped, re.S)
    return match.group(0) if match else stripped


def parse_json_safely(text):
    try:
        return json.loads(extract_json_text(text))
    except Exception:
        return None


def has_chat_html_contamination(content):
    """메시지 내용에 카카오톡 렌더링용 HTML이 섞였는지 확인합니다."""
    if content is None:
        return False
    raw = html.unescape(str(content))
    raw = raw.replace('\\"', '"').replace("\\'", "'")
    danger_tokens = [
        "kakao-row",
        "kakao-bubble",
        "kakao-message-block",
        "kakao-chat-wrap",
        "<div",
        "</div>",
        "&lt;div",
        "class=",
    ]
    return any(token in raw for token in danger_tokens)


def clean_chat_content(content, role=None):
    """
    채팅 메시지에 HTML/CSS/코드가 섞여 들어간 경우 실제 발화만 추출합니다.
    추출에 실패하면 HTML 원문을 절대 출력하지 않고 빈 문자열/안내문으로 대체합니다.
    """
    if content is None:
        return ""

    original = str(content)
    text = original.strip()

    # 코드블록 제거
    text = re.sub(r"^```(?:html|python|text)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text)

    # &lt;div ...&gt; 형태와 역슬래시로 이스케이프된 따옴표를 모두 복원
    text = html.unescape(text)
    text = text.replace('\\"', '"').replace("\\'", "'")

    # style/script 제거
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.I)

    # 카카오 말풍선 HTML이 저장된 경우: role에 맞는 말풍선 내용만 추출
    if "kakao-bubble" in text or "kakao-row" in text or "kakao-message-block" in text:
        bubble_pattern = re.compile(
            r'<div\s+class=["\']kakao-bubble\s+(teacher|student)["\'][^>]*>(.*?)</div>',
            flags=re.S | re.I
        )
        bubbles = bubble_pattern.findall(text)

        if bubbles:
            desired = "teacher" if role == "user" else "student" if role == "assistant" else None
            if desired:
                matched = [body for bubble_role, body in bubbles if bubble_role.lower() == desired]
                text = matched[-1] if matched else bubbles[-1][1]
            else:
                text = bubbles[-1][1]
        else:
            # 추출 실패 시 원문 HTML을 보여주지 않음
            return ""

    # 일반 HTML 태그 제거
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)

    # 엔티티 복원 및 공백 정리
    text = html.unescape(text)
    text = text.replace('\\"', '"').replace("\\'", "'")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    text = text.strip()

    # HTML 잔해가 남으면 절대 출력하지 않음
    if has_chat_html_contamination(text):
        return ""

    return text


def sanitize_sim_messages():
    """세션에 저장된 상담 대화에서 HTML 코드 잔해를 제거합니다."""
    cleaned_messages = []
    had_contamination = False

    for msg in st.session_state.get("sim_messages", []):
        role = msg.get("role", "assistant")
        raw_content = msg.get("content", "")
        if has_chat_html_contamination(raw_content):
            had_contamination = True
        cleaned = clean_chat_content(raw_content, role=role)
        if cleaned:
            cleaned_messages.append({"role": role, "content": cleaned})

    # HTML이 섞인 세션이면, 추출 가능한 실제 발화만 남기고 HTML은 버림
    st.session_state["sim_messages"] = cleaned_messages

    # 모든 메시지가 HTML 잔해 때문에 사라졌는데 시뮬레이션은 시작된 상태면 첫 문장 복구
    if had_contamination and not cleaned_messages and "sim_profile" in st.session_state:
        st.session_state["sim_messages"] = [
            {"role": "assistant", "content": "선생님... 무슨 이야기부터 해야 할지 잘 모르겠어요."}
        ]

def render_kakao_chat(messages):
    """
    카카오톡 스타일 상담 대화창 렌더링.
    st.markdown으로 긴 HTML을 렌더링하면 Markdown이 일부 HTML을 코드블록으로 오해할 수 있어
    components.html iframe으로 분리해서 렌더링합니다.
    """
    rows_html = ""

    if not messages:
        rows_html += '<div class="empty-chat">아직 대화가 없습니다. 시뮬레이션을 시작해보세요.</div>'
    else:
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            cleaned_content = clean_chat_content(content, role=role)

            # HTML 잔해가 추출 실패로 남은 경우 화면에 코드로 보이지 않도록 건너뜀
            if not cleaned_content:
                continue

            safe_content = html.escape(cleaned_content).replace("\n", "<br>")

            if role == "user":
                rows_html += (
                    '<div class="kakao-row teacher">'
                    '<div class="kakao-message-block">'
                    '<div class="kakao-name right">교사</div>'
                    f'<div class="kakao-bubble teacher">{safe_content}</div>'
                    '<div class="kakao-time right">방금 전</div>'
                    '</div>'
                    '</div>'
                )
            else:
                rows_html += (
                    '<div class="kakao-row student">'
                    '<div class="kakao-avatar">👤</div>'
                    '<div class="kakao-message-block">'
                    '<div class="kakao-name">AI 학생</div>'
                    f'<div class="kakao-bubble student">{safe_content}</div>'
                    '<div class="kakao-time">방금 전</div>'
                    '</div>'
                    '</div>'
                )

    # components.html은 별도 iframe이라, 필요한 CSS를 여기 안에 같이 넣어야 함
    chat_html = f"""
    <!doctype html>
    <html>
    <head>
    <meta charset="utf-8" />
    <style>
        html, body {{
            margin: 0;
            padding: 0;
            background: transparent;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }}
        .kakao-chat-wrap {{
            box-sizing: border-box;
            width: 100%;
            min-height: 420px;
            max-height: 620px;
            overflow-y: auto;
            background-color: #B8C9D6;
            border: 1px solid #9FB2C0;
            border-radius: 18px;
            padding: 24px;
        }}
        .kakao-row {{
            display: flex;
            align-items: flex-start;
            margin-bottom: 16px;
        }}
        .kakao-row.student {{ justify-content: flex-start; }}
        .kakao-row.teacher {{ justify-content: flex-end; }}
        .kakao-avatar {{
            width: 38px;
            height: 38px;
            border-radius: 50%;
            background: #8DD3E5;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 10px;
            font-size: 20px;
            flex-shrink: 0;
        }}
        .kakao-message-block {{ max-width: 72%; }}
        .kakao-name {{
            font-size: 13px;
            color: #263238;
            margin-bottom: 4px;
            font-weight: 700;
        }}
        .kakao-name.right {{ text-align: right; }}
        .kakao-bubble {{
            display: inline-block;
            padding: 12px 15px;
            border-radius: 16px;
            font-size: 16px;
            line-height: 1.55;
            color: #111827;
            word-break: keep-all;
            white-space: pre-wrap;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        }}
        .kakao-bubble.student {{
            background-color: #FFFFFF;
            border-top-left-radius: 4px;
        }}
        .kakao-bubble.teacher {{
            background-color: #FEE500;
            border-top-right-radius: 4px;
        }}
        .kakao-time {{
            font-size: 11px;
            color: #455A64;
            margin-top: 4px;
        }}
        .kakao-time.right {{ text-align: right; }}
        .empty-chat {{
            color: #263238;
            text-align: center;
            padding: 80px 0;
            font-size: 15px;
        }}
    </style>
    </head>
    <body>
        <div class="kakao-chat-wrap" id="chat-wrap">
            {rows_html}
        </div>
        <script>
            const el = document.getElementById('chat-wrap');
            if (el) {{ el.scrollTop = el.scrollHeight; }}
        </script>
    </body>
    </html>
    """

    components.html(chat_html, height=650, scrolling=False)

def get_dev_mode():
    return DEV_MODE


def get_admin_password():
    try:
        return st.secrets.get("ADMIN_PASSWORD", "")
    except Exception:
        return ""


def build_prompt(data):
    return f"""
너는 담임교사의 학생 상담을 보조하는 AI 분석 도우미다.

[자료 기반 응답 원칙]
1. 가능하면 업로드된 상담 매뉴얼, 문제행동별 개입 지도서, 학교상담 운영 자료, 위기 사안 대응 자료를 근거로 분석한다.
2. 자료에서 확인할 수 없는 내용은 추측하지 않는다.
3. 학생을 의학적으로 진단하거나 낙인찍지 않는다.
4. 자해, 자살, 학대, 성폭력, 학교폭력 등 위기 사안은 일반 상담 조언으로만 처리하지 않고 전문상담교사, 보호자, Wee센터, 관련 기관 연계를 우선 고려한다.
5. 분석 결과에는 교사가 실제 상담에서 참고할 수 있는 방향을 제시한다.

다음 상담 기록을 바탕으로 학생 유형, 위험도, 상담 목표, 교사 피드백 방향을 분석하라.

중요 원칙:
1. 학생을 진단하거나 낙인찍지 않는다.
2. AI 분석 결과는 교사의 판단을 보조하는 참고자료로만 작성한다.
3. 이름, 학교명, 전화번호, 주소 등 개인정보는 출력하지 않는다.
4. 자해, 자살, 학대, 심각한 폭력 피해가 의심되면 일반 상담이 아니라 즉시개입으로 분류한다.
5. 위기신호가 있으면 보호자, 전문상담교사, Wee센터, 청소년상담복지센터 등 연계 필요성을 제시한다.

[상담 기록]
- 익명 학생 ID: {data["student_id"]}
- 학년: {data["grade"]}
- 상담 경로: {data["referral_source"]}
- 상담 주제: {data["topic"]}
- 관찰 내용: {data["observation"]}
- 학생 발화: {data["student_statement"]}
- 위험 신호 체크: {data["risk_check"]}
- 교사 메모: {data["teacher_memo"]}

[학생 유형 목록]
{chr(10).join(TYPE_MANUAL.keys())}

아래 JSON 형식으로만 출력하라.

{{
  "추정학생유형": "",
  "분류근거": "",
  "주요감정": [],
  "위험요인": [],
  "보호요인": [],
  "위험도": "낮음/중간/높음/즉시개입",
  "교사상담목표": "",
  "다음상담질문": ["", "", ""],
  "학생피드백문장": "",
  "보호자상담필요": "예/아니오",
  "전문기관연계필요": "예/아니오",
  "추천후속활동": "",
  "윤리주의사항": ""
}}
"""


def save_result(input_data, analysis_data, raw_text):
    row = {
        "저장일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "익명학생ID": input_data.get("student_id", ""),
        "학년": input_data.get("grade", ""),
        "상담경로": input_data.get("referral_source", ""),
        "상담주제": input_data.get("topic", ""),
        "관찰내용": input_data.get("observation", ""),
        "학생발화": input_data.get("student_statement", ""),
        "위험신호체크": input_data.get("risk_check", ""),
        "교사메모": input_data.get("teacher_memo", ""),
        "추정학생유형": analysis_data.get("추정학생유형", "") if analysis_data else "",
        "위험도": analysis_data.get("위험도", "") if analysis_data else "",
        "교사상담목표": analysis_data.get("교사상담목표", "") if analysis_data else "",
        "전문기관연계필요": analysis_data.get("전문기관연계필요", "") if analysis_data else "",
        "AI원문결과": raw_text
    }

    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE, encoding="utf-8-sig")
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    else:
        df = pd.DataFrame([row])

    df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")


def load_results():
    if os.path.exists(DATA_FILE):
        try:
            return pd.read_csv(DATA_FILE, encoding="utf-8-sig")
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()


def reset_simulation_state():
    for key in ["sim_messages", "sim_feedback", "sim_feedback_json", "sim_profile"]:
        if key in st.session_state:
            del st.session_state[key]


def make_feedback_chart(scores):
    if not scores:
        st.info("점수 데이터가 없어 레이더 차트를 표시할 수 없습니다.")
        return

    categories = ["감정 반응", "질문 방식", "해결책 제시", "감정 완화", "대화 자연스러움", "윤리 준수"]
    values = [float(scores.get(c, 0)) for c in categories]
    categories_closed = categories + [categories[0]]
    values_closed = values + [values[0]]

    if go is None:
        st.warning("plotly가 설치되어 있지 않아 차트를 표시할 수 없습니다. requirements.txt에 plotly를 추가하세요.")
        st.write(pd.DataFrame({"역량": categories, "점수": values}))
        return

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values_closed,
        theta=categories_closed,
        fill="toself",
        name="상담 역량"
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
        showlegend=False,
        height=420,
        margin=dict(l=40, r=40, t=40, b=40)
    )
    st.plotly_chart(fig, use_container_width=True)


def render_feedback_result():
    feedback_json = st.session_state.get("sim_feedback_json")
    feedback_text = st.session_state.get("sim_feedback")

    if feedback_json:
        scores = feedback_json.get("scores", {})
        summary = feedback_json.get("summary", {})

        st.markdown("### 상담 피드백 결과")

        col1, col2, col3 = st.columns(3)
        if scores:
            avg_score = sum(float(v) for v in scores.values()) / len(scores)
        else:
            avg_score = 0

        good_points = summary.get("잘한점", [])
        improve_points = summary.get("보완점", [])

        col1.metric("종합 점수", f"{avg_score:.1f} / 5")
        col2.metric("잘한 점", f"{len(good_points)}개")
        col3.metric("보완점", f"{len(improve_points)}개")

        make_feedback_chart(scores)

        st.markdown("#### 종합 피드백")
        st.write(summary.get("종합피드백", ""))

        st.markdown("#### 잘한 점")
        for item in good_points:
            st.write(f"- {item}")

        st.markdown("#### 보완할 점")
        for item in improve_points:
            st.write(f"- {item}")

        st.markdown("#### 다음 상담에서 해볼 질문")
        for idx, item in enumerate(summary.get("다음질문", []), start=1):
            st.write(f"{idx}. {item}")

        st.markdown("#### 주의사항")
        st.warning(summary.get("주의사항", ""))
    elif feedback_text:
        st.markdown("### 상담 피드백 결과")
        st.markdown(feedback_text)



# =========================
# 사이드바: 관리자 모드
# =========================

with st.sidebar:
    st.header("사용 안내")
    st.write("1. AI 상담 연습에서 학생과 대화합니다.")
    st.write("2. 상담 피드백을 받아 교사 발화를 점검합니다.")
    st.write("3. 상담기록 분석은 기존 상담 기록을 분석할 때 사용합니다.")
    st.warning("실제 학생 이름, 학교명, 연락처 등 개인정보는 입력하지 마세요.")

    st.markdown("---")
    st.subheader("관리자 모드")
    if st.session_state.get("admin_mode"):
        st.success("관리자 모드 활성화")
        if st.button("관리자 로그아웃"):
            st.session_state["admin_mode"] = False
            st.rerun()
    else:
        admin_pw = st.text_input("관리자 비밀번호", type="password")
        if st.button("관리자 로그인"):
            saved_pw = get_admin_password()
            if saved_pw and admin_pw == saved_pw:
                st.session_state["admin_mode"] = True
                st.success("관리자 모드로 전환되었습니다.")
                st.rerun()
            elif not saved_pw:
                st.warning("ADMIN_PASSWORD가 Secrets에 설정되어 있지 않습니다.")
            else:
                st.error("비밀번호가 올바르지 않습니다.")


# =========================
# 화면 상단
# =========================

st.markdown("""
<div class="title-box">
    <h1>🧠 티처 토닥</h1>
    <p>AI 학생과 상담을 연습하고, 상담 기록을 분석하는 교사용 상담 지원 프로토타입</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="notice-box">
    본 시스템은 상담자의 판단을 보조하기 위한 프로토타입입니다.
    AI 분석 결과는 최종 판단이 아니며, 자해·자살·학대·폭력 등 위기 신호가 있는 경우 즉시 전문상담교사 및 관련 기관과 연계해야 합니다.
</div>
""", unsafe_allow_html=True)

# 관리자 여부에 따라 탭 동적 구성
tab_labels = ["🏠 시작하기", "💬 AI 상담 연습", "📝 상담기록 분석", "📚 유형별 매뉴얼"]
if st.session_state.get("admin_mode"):
    tab_labels.append("📊 관리자 대시보드")

tabs = st.tabs(tab_labels)
tab_home = tabs[0]
tab_sim = tabs[1]
tab_analysis = tabs[2]
tab_manual = tabs[3]
tab_dashboard = tabs[4] if len(tabs) > 4 else None


# =========================
# 🏠 시작하기
# =========================

with tab_home:
    st.subheader("무엇을 해볼까요?")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div class="small-guide">
        <h3>💬 AI 상담 연습</h3>
        <p>AI가 학생 역할을 하고, 교사는 상담 대화를 연습한 뒤 피드백을 받습니다.</p>
        <b>추천 체험 기능</b>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="small-guide">
        <h3>📝 상담기록 분석</h3>
        <p>상담 기록을 입력하면 AI가 학생 유형, 위험도, 상담 방향을 분석합니다.</p>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class="small-guide">
        <h3>📚 유형별 매뉴얼</h3>
        <p>학생 유형별 특징, 상담 목표, 질문 예시를 확인합니다.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("### 추천 사용 순서")
    st.write("1. **💬 AI 상담 연습** 탭에서 학생 유형을 선택하고 시뮬레이션을 시작합니다.")
    st.write("2. 교사 역할로 상담 질문을 입력하고 AI 학생과 3~5회 대화합니다.")
    st.write("3. **내 상담 피드백 받기**를 눌러 강점과 보완점을 확인합니다.")
    st.write("4. 필요 시 **📝 상담기록 분석**에서 상담 기록을 분석하고 저장합니다.")
    st.warning("실제 학생 이름, 학교명, 연락처 등 개인정보는 입력하지 마세요.")


# =========================
# 💬 AI 상담 연습
# =========================

with tab_sim:
    st.subheader("💬 AI 상담 연습")
    st.info("사용자는 교사 역할입니다. 아래 채팅창에 학생에게 할 상담 질문을 입력하면 AI가 학생 역할로 답변합니다.")

    sim_started = "sim_profile" in st.session_state

    if sim_started:
        profile = st.session_state["sim_profile"]
        m1, m2, m3 = st.columns(3)
        m1.metric("학생 유형", profile.get("type", ""))
        m2.metric("상담 주제", profile.get("topic", ""))
        teacher_turns = len([m for m in st.session_state.get("sim_messages", []) if m["role"] == "user"])
        m3.metric("교사 발화 수", teacher_turns)

        with st.expander("학생 설정 보기/수정", expanded=False):
            sim_grade = st.text_input("시뮬레이션 학생 학년", value=profile.get("grade", "중학교 3학년"), key="sim_grade_edit")
            sim_type = st.selectbox("시뮬레이션 학생 유형", list(TYPE_MANUAL.keys()), index=list(TYPE_MANUAL.keys()).index(profile.get("type")) if profile.get("type") in TYPE_MANUAL else 0, key="sim_type_edit")
            sim_topic = st.text_input("상담 주제", value=profile.get("topic", "진로·성적 불안"), key="sim_topic_edit")
            sim_personality = st.text_input("학생 성향", value=profile.get("personality", "조심스럽고 감정을 잘 표현하지 않음"), key="sim_personality_edit")
            sim_background = st.text_area("학생 배경 상황", value=profile.get("background", ""), height=100, key="sim_background_edit")
            if st.button("학생 설정 업데이트"):
                st.session_state["sim_profile"] = {
                    "grade": sim_grade,
                    "type": sim_type,
                    "topic": sim_topic,
                    "personality": sim_personality,
                    "background": sim_background
                }
                st.success("학생 설정이 업데이트되었습니다.")
                st.rerun()
    else:
        sim_col1, sim_col2 = st.columns(2)
        with sim_col1:
            sim_grade = st.text_input("시뮬레이션 학생 학년", value="중학교 3학년")
            sim_type = st.selectbox("시뮬레이션 학생 유형", list(TYPE_MANUAL.keys()), key="sim_type")
        with sim_col2:
            sim_topic = st.text_input("상담 주제", value="진로·성적 불안")
            sim_personality = st.text_input("학생 성향", value="조심스럽고 감정을 잘 표현하지 않음")

        sim_background = st.text_area(
            "학생 배경 상황",
            value="고등학교 진학과 성적 부담으로 걱정이 많고, 최근 수업 집중도가 떨어짐.",
            height=100
        )

    if "sim_messages" not in st.session_state:
        st.session_state["sim_messages"] = []

    # 이전 세션에 HTML 코드가 메시지로 저장된 경우 자동 정리
    sanitize_sim_messages()

    start_col, reset_col = st.columns([2, 1])
    with start_col:
        if st.button("AI 학생과 상담 시작", type="primary", use_container_width=True):
            st.session_state["sim_profile"] = {
                "grade": sim_grade,
                "type": sim_type,
                "topic": sim_topic,
                "personality": sim_personality,
                "background": sim_background
            }
            st.session_state["sim_messages"] = [
                {"role": "assistant", "content": "선생님... 무슨 이야기부터 해야 할지 잘 모르겠어요."}
            ]
            for key in ["sim_feedback", "sim_feedback_json"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    with reset_col:
        reset_check = st.checkbox("초기화 확인")
        if st.button("초기화 실행", use_container_width=True, disabled=not reset_check):
            reset_simulation_state()
            st.success("대화가 초기화되었습니다. 다시 시뮬레이션을 시작해주세요.")
            st.rerun()

    st.markdown("---")

    st.markdown(
        '<div class="chat-section-title">💬 상담 대화창</div>',
        unsafe_allow_html=True
    )

    render_kakao_chat(st.session_state.get("sim_messages", []))

    if "sim_profile" not in st.session_state:
        st.info("먼저 학생 정보를 설정한 뒤, **AI 학생과 상담 시작** 버튼을 눌러주세요.")
        user_input = None
    else:
        st.markdown(
            '<div class="chat-input-guide">아래 입력창에 교사 역할로 학생에게 할 상담 질문을 입력하세요.</div>',
            unsafe_allow_html=True
        )
        user_input = st.chat_input("교사로서 학생에게 상담 질문을 입력하세요.")

    if user_input:
        st.session_state["sim_messages"].append({"role": "user", "content": user_input})
        profile = st.session_state["sim_profile"]

        conversation_text = ""
        for msg in st.session_state["sim_messages"]:
            speaker = "교사" if msg["role"] == "user" else "학생"
            conversation_text += f"{speaker}: {clean_chat_content(msg.get('content', ''), role=msg.get('role', ''))}\n"

        persona_rule_text = "\n".join([f"- {rule}" for rule in PERSONA_RULES.get(profile["type"], [])])
        manual = TYPE_MANUAL.get(profile["type"], {})
        manual_context = f"""
학생 유형: {profile["type"]}
특징: {manual.get("특징", "")}
상담목표: {manual.get("상담목표", "")}
피드백 방향: {manual.get("피드백", "")}
"""

        student_prompt = f"""
너는 학생 상담 시뮬레이션에서 '학생 역할'을 맡는다.
사용자는 교사 역할이다.

[학생 정보]
- 학년: {profile["grade"]}
- 학생 유형: {profile["type"]}
- 상담 주제: {profile["topic"]}
- 학생 성향: {profile["personality"]}
- 배경 상황: {profile["background"]}

[제공된 상담 기준 자료]
{manual_context}

[선택된 학생 유형의 페르소나 규칙]
{persona_rule_text}

[역할 지침]
1. 너는 AI 상담사가 아니라 학생이다.
2. 교사를 평가하거나 조언하지 말고, 학생처럼 자연스럽게 답하라.
3. 한 번에 너무 많은 정보를 말하지 말고, 실제 학생처럼 조금씩 감정을 드러내라.
4. 선택된 학생 유형의 페르소나 규칙을 말투와 반응에 반영하라.
5. 자해, 자살, 학대, 폭력 피해 등 위기 신호는 자극적으로 묘사하지 말고 안전한 범위에서 간접적 신호만 드러내라.
6. 답변은 1~4문장 정도로 짧게 하라.
7. 제공된 학생 정보와 상담 기준 자료를 벗어난 전문적 진단이나 조언은 하지 말라.

[지금까지의 대화]
{conversation_text}

마지막 교사의 말에 대해 학생 입장에서 답하라.
"""

        try:
            with st.spinner("AI 학생이 답변을 준비하고 있습니다..."):
                response = client.responses.create(
                    model="gpt-4.1-mini",
                    input=student_prompt
                )
            ai_reply = response.output_text
            st.session_state["sim_messages"].append({"role": "assistant", "content": ai_reply})
            st.rerun()
        except Exception as e:
            st.error(f"학생 응답 생성 중 오류가 발생했습니다: {e}")

    st.markdown("---")

    if st.button("내 상담 피드백 받기", type="primary"):
        if len(st.session_state.get("sim_messages", [])) < 3:
            st.warning("상담 대화가 너무 짧습니다. 최소 2~3회 이상 대화한 뒤 피드백을 받아보세요.")
        else:
            profile = st.session_state.get("sim_profile", {})
            conversation_text = ""
            for msg in st.session_state["sim_messages"]:
                speaker = "교사" if msg["role"] == "user" else "학생"
                conversation_text += f"{speaker}: {clean_chat_content(msg.get('content', ''), role=msg.get('role', ''))}\n"

            feedback_prompt = f"""
            
너는 교사 상담 훈련을 돕는 슈퍼바이저다.
아래 상담 시뮬레이션 대화를 보고 교사의 상담 역량을 평가하라.

[자료 기반 피드백 원칙]
1. 가능하면 업로드된 상담 매뉴얼, 개입 지도서, 학교상담 운영 자료, 위기 사안 대응 자료를 근거로 피드백한다.
2. 자료에 없는 내용을 단정하지 않는다.
3. 교사의 상담 발화가 학생의 감정 탐색, 공감, 위험 신호 확인, 보호자 및 전문기관 연계 측면에서 적절했는지 평가한다.
4. 자해, 자살, 학대, 성폭력, 학교폭력 등 위기 신호가 보이면 일반적 상담 조언보다 안전 확보와 연계를 우선 제안한다.
5. 피드백은 교사를 비난하지 말고, 다음 상담에서 개선할 수 있는 행동 중심으로 작성한다.

[학생 정보]
- 학년: {profile.get("grade", "")}
- 학생 유형: {profile.get("type", "")}
- 상담 주제: {profile.get("topic", "")}
- 학생 성향: {profile.get("personality", "")}
- 배경 상황: {profile.get("background", "")}

[상담 대화]
{conversation_text}

[평가 기준]
1. 감정 반응: 학생의 감정을 공감하고 반영했는가?
2. 질문 방식: 열린 질문과 탐색 질문을 적절히 사용했는가?
3. 해결책 제시: 해결책을 너무 빠르게 제시하지 않았는가?
4. 감정 완화: 학생의 불안과 긴장을 낮추는 데 기여했는가?
5. 대화 자연스러움: 실제 상담처럼 자연스럽게 대화했는가?
6. 윤리 준수: 위험 신호, 개인정보, 전문기관 연계 기준을 고려했는가?

반드시 아래 JSON 형식으로만 출력하라.
점수는 각 항목 1~5점 정수로 입력하라.

{{
  "scores": {{
    "감정 반응": 0,
    "질문 방식": 0,
    "해결책 제시": 0,
    "감정 완화": 0,
    "대화 자연스러움": 0,
    "윤리 준수": 0
  }},
  "summary": {{
    "종합피드백": "",
    "잘한점": ["", ""],
    "보완점": ["", ""],
    "다음질문": ["", "", ""],
    "주의사항": ""
  }}
}}
"""
            try:
                with st.spinner("피드백 분석 중입니다. 예상 소요 시간은 약 30초 이내입니다."):
                    if "VECTOR_STORE_ID" in st.secrets:
                        response = client.responses.create(
                            model="gpt-4.1-mini",
                            input=feedback_prompt,
                            tools=[
                                {
                                    "type": "file_search",
                                    "vector_store_ids": [st.secrets["VECTOR_STORE_ID"]],
                                    "max_num_results": 5
                                }
                            ]
                        )
                    else:
                        response = client.responses.create(
                            model="gpt-4.1-mini",
                            input=feedback_prompt
                        )
                feedback_text = response.output_text
                feedback_json = parse_json_safely(feedback_text)
                st.session_state["sim_feedback"] = feedback_text
                st.session_state["sim_feedback_json"] = feedback_json
                st.rerun()
            except Exception as e:
                st.error(f"피드백 생성 중 오류가 발생했습니다: {e}")

    render_feedback_result()


# =========================
# 📝 상담기록 분석
# =========================

with tab_analysis:
    st.subheader("📝 상담기록 분석")
    st.info("기존 상담 기록을 입력하면 AI가 학생 유형, 위험도, 상담 방향을 분석합니다.")

    sample_name = st.selectbox("샘플 데이터 불러오기", ["직접 입력"] + list(SAMPLE_DATA.keys()))

    if sample_name != "직접 입력":
        selected = SAMPLE_DATA[sample_name]
    else:
        selected = {
            "student_id": "U-0004",
            "grade": "",
            "referral_source": "",
            "topic": "",
            "observation": "",
            "student_statement": "",
            "risk_check": "없음",
            "teacher_memo": ""
        }

    col1, col2, col3 = st.columns(3)
    with col1:
        student_id = st.text_input("익명 학생 ID", value=selected["student_id"], placeholder="예: U-0001")
    with col2:
        grade = st.text_input("학년", value=selected["grade"], placeholder="예: 중학교 3학년")
    with col3:
        referral_source = st.text_input("상담 경로", value=selected["referral_source"], placeholder="예: 담임 관찰, 자기 의뢰, 학부모 요청")

    topic = st.text_input("상담 주제", value=selected["topic"], placeholder="예: 진로·학업 불안, 친구관계 갈등")

    observation = st.text_area(
        "관찰 내용",
        value=selected["observation"],
        placeholder="예: 최근 수업 집중도가 낮아지고 쉬는 시간에 혼자 있는 시간이 늘어남",
        height=140
    )

    student_statement = st.text_area(
        "학생 발화",
        value=selected["student_statement"],
        placeholder="예: 요즘 공부하려고 앉아도 걱정만 나요",
        height=120
    )

    risk_check = st.text_area(
        "위험 신호 체크",
        value=selected["risk_check"],
        placeholder="예: 자해·자살 언급 없음 / 학교폭력 피해 여부 확인 필요",
        height=80
    )

    teacher_memo = st.text_area(
        "교사 메모",
        value=selected["teacher_memo"],
        placeholder="예: 즉각적 위기 신호는 없으나 불안이 학습 집중에 영향을 주는 것으로 보임",
        height=100
    )

    current_data = {
        "student_id": student_id,
        "grade": grade,
        "referral_source": referral_source,
        "topic": topic,
        "observation": observation,
        "student_statement": student_statement,
        "risk_check": risk_check,
        "teacher_memo": teacher_memo
    }

    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("상담기록 분석 시작", type="primary", use_container_width=True):
            prompt = build_prompt(current_data)
            with st.spinner("AI가 상담 기록을 분석하고 있습니다..."):
                try:
                    result_text = analyze_with_openai(prompt)
                    result_json = parse_json_safely(result_text)

                    st.session_state["last_input"] = current_data
                    st.session_state["last_result_text"] = result_text
                    st.session_state["last_result_json"] = result_json
                    st.success("AI 분석이 완료되었습니다.")
                except Exception as e:
                    st.error(f"분석 중 오류가 발생했습니다: {e}")

    with btn_col2:
        if get_dev_mode():
            if st.button("프롬프트만 확인하기", use_container_width=True):
                st.code(build_prompt(current_data), language="text")

    result_json = st.session_state.get("last_result_json")
    result_text = st.session_state.get("last_result_text")
    last_input = st.session_state.get("last_input")

    st.markdown("---")
    st.markdown("### AI 분석 결과")

    if not result_text:
        st.info("아직 분석 결과가 없습니다. 상담 기록을 입력한 뒤 **상담기록 분석 시작**을 눌러주세요.")
    else:
        if result_json:
            c1, c2, c3 = st.columns(3)
            c1.metric("추정 학생 유형", result_json.get("추정학생유형", ""))
            c2.metric("위험도", result_json.get("위험도", ""))
            c3.metric("전문기관 연계", result_json.get("전문기관연계필요", ""))

            st.write("**분류 근거**")
            st.write(result_json.get("분류근거", ""))

            st.write("**주요 감정**")
            st.write(", ".join(result_json.get("주요감정", [])))

            st.write("**위험 요인**")
            st.write(", ".join(result_json.get("위험요인", [])))

            st.write("**보호 요인**")
            st.write(", ".join(result_json.get("보호요인", [])))

            st.write("**교사 상담 목표**")
            st.write(result_json.get("교사상담목표", ""))

            st.write("**다음 상담 질문**")
            for q in result_json.get("다음상담질문", []):
                st.write(f"- {q}")

            st.write("**학생 피드백 문장**")
            st.info(result_json.get("학생피드백문장", ""))

            st.write("**추천 후속 활동**")
            st.write(result_json.get("추천후속활동", ""))

            st.write("**윤리 주의사항**")
            st.warning(result_json.get("윤리주의사항", ""))

            if st.button("분석 결과 저장하기"):
                save_result(last_input, result_json, result_text)
                st.success("저장 완료: counsel_results.csv 파일이 생성/업데이트되었습니다.")
        else:
            st.warning("AI 응답이 JSON으로 깔끔하게 변환되지 않았습니다. 원문을 확인하세요.")
            st.code(result_text, language="text")

    st.markdown("---")
    st.markdown("### 저장된 상담 기록 히스토리")
    st.warning("실제 학생 이름, 학교명, 연락처 등 개인정보는 입력하지 마세요.")

    df_history = load_results()
    if df_history.empty:
        st.info("아직 저장된 상담 기록이 없습니다.")
    else:
        search_topic = st.text_input("상담주제 검색", placeholder="예: 진로, 친구관계, 스마트폰")
        risk_options = ["전체"] + sorted([str(x) for x in df_history.get("위험도", pd.Series(dtype=str)).dropna().unique()])
        type_options = ["전체"] + sorted([str(x) for x in df_history.get("추정학생유형", pd.Series(dtype=str)).dropna().unique()])

        fc1, fc2 = st.columns(2)
        with fc1:
            selected_risk = st.selectbox("위험도 필터", risk_options)
        with fc2:
            selected_type = st.selectbox("학생 유형 필터", type_options)

        filtered = df_history.copy()
        if search_topic and "상담주제" in filtered.columns:
            filtered = filtered[filtered["상담주제"].astype(str).str.contains(search_topic, case=False, na=False)]
        if selected_risk != "전체" and "위험도" in filtered.columns:
            filtered = filtered[filtered["위험도"].astype(str) == selected_risk]
        if selected_type != "전체" and "추정학생유형" in filtered.columns:
            filtered = filtered[filtered["추정학생유형"].astype(str) == selected_type]

        display_cols = [c for c in ["저장일시", "익명학생ID", "학년", "상담주제", "추정학생유형", "위험도", "전문기관연계필요"] if c in filtered.columns]
        st.dataframe(filtered[display_cols], use_container_width=True)

        if not filtered.empty:
            row_labels = [f"{i} | {row.get('저장일시', '')} | {row.get('익명학생ID', '')} | {row.get('상담주제', '')}" for i, row in filtered.iterrows()]
            selected_label = st.selectbox("상세 열람할 기록 선택", row_labels)
            selected_idx = int(selected_label.split(" | ")[0])
            selected_row = filtered.loc[selected_idx]

            with st.expander("선택한 상담 기록 상세 보기", expanded=True):
                st.write("**관찰 내용**")
                st.write(selected_row.get("관찰내용", ""))
                st.write("**학생 발화**")
                st.write(selected_row.get("학생발화", ""))
                st.write("**교사 메모**")
                st.write(selected_row.get("교사메모", ""))
                st.write("**AI 원문 결과**")
                st.code(str(selected_row.get("AI원문결과", "")), language="text")


# =========================
# 📚 유형별 매뉴얼
# =========================

with tab_manual:
    st.subheader("📚 유형별 상담 매뉴얼")

    selected_type = st.selectbox("학생 유형 선택", list(TYPE_MANUAL.keys()))
    manual = TYPE_MANUAL[selected_type]

    st.markdown(f"### {selected_type}")
    st.write("**주요 특징**")
    st.write(manual["특징"])

    st.write("**상담 목표**")
    st.write(manual["상담목표"])

    st.write("**교사 질문 예시**")
    for q in manual["교사질문"]:
        st.write(f"- {q}")

    st.write("**학생 피드백 문장**")
    st.info(manual["피드백"])


# =========================
# 📊 관리자 대시보드
# =========================

if tab_dashboard is not None:
    with tab_dashboard:
        st.subheader("📊 관리자 대시보드")
        st.info("이 화면은 상담기록 분석에서 저장한 결과를 누적해 보여주는 관리자용 화면입니다. AI 상담 연습 결과는 현재 반영되지 않습니다.")

        df = load_results()

        if df.empty:
            st.info("아직 저장된 상담 결과가 없습니다.")
        else:
            total_count = len(df)
            high_risk_count = len(df[df["위험도"].isin(["높음", "즉시개입"])])
            referral_count = len(df[df["전문기관연계필요"] == "예"])

            col1, col2, col3 = st.columns(3)
            col1.metric("전체 상담 건수", total_count)
            col2.metric("높음/즉시개입", high_risk_count)
            col3.metric("전문기관 연계 필요", referral_count)

            st.markdown("### 유형별 상담 건수")
            if "추정학생유형" in df.columns:
                st.bar_chart(df["추정학생유형"].value_counts())

            st.markdown("### 위험도별 상담 건수")
            if "위험도" in df.columns:
                st.bar_chart(df["위험도"].value_counts())

            st.markdown("### 저장 데이터")
            st.dataframe(df, use_container_width=True)
