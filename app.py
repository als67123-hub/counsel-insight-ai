import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from openai import OpenAI

# =========================
# 기본 설정
# =========================

st.set_page_config(
    page_title="Counsel Insight AI",
    page_icon="🧠",
    layout="wide"
)

DATA_FILE = "counsel_results.csv"

# 여기에 본인 OpenAI API 키 입력
# 예: client = OpenAI(api_key="sk-...")
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])


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
# CSS 디자인
# =========================

st.markdown("""
<style>
.main {
    background-color: #F7F9FC;
}
.block-container {
    padding-top: 2rem;
}
.title-box {
    background: linear-gradient(135deg, #1F4E79, #2E75B6);
    padding: 28px;
    border-radius: 18px;
    color: white;
    margin-bottom: 20px;
}
.notice-box {
    background-color: #FFF7ED;
    border: 1px solid #FDBA74;
    color: #7C2D12;
    padding: 14px;
    border-radius: 12px;
    margin-bottom: 20px;
}
.result-card {
    background-color: white;
    padding: 18px;
    border-radius: 14px;
    border: 1px solid #E5E7EB;
    margin-bottom: 12px;
}
</style>
""", unsafe_allow_html=True)


# =========================
# 함수
# =========================

def build_prompt(data):
    return f"""
너는 담임교사의 학생 상담을 보조하는 AI 분석 도우미다.

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
T01 친구관계 어려움형
T02 불안·걱정형
T03 무기력·우울형
T04 분노·공격형
T05 산만·충동형
T06 스마트폰·인터넷 과의존형
T07 규칙 미준수형
T08 등교곤란·학업중단 위험형
T09 고립·은둔형
T10 위기신호형

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


def analyze_with_openai(prompt):
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )
    return response.output_text


def parse_json_safely(text):
    try:
        return json.loads(text)
    except Exception:
        return None


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
        return pd.read_csv(DATA_FILE, encoding="utf-8-sig")
    return pd.DataFrame()

# =========================
# 화면
# =========================

st.markdown("""
<div class="title-box">
    <h1>🧠 Counsel Insight AI</h1>
    <p>학생 상담 데이터 분석 및 교사용 상담 매뉴얼 프로토타입</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="notice-box">
    본 시스템은 상담자의 판단을 보조하기 위한 프로토타입입니다.
    AI 분석 결과는 최종 판단이 아니며, 자해·자살·학대·폭력 등 위기 신호가 있는 경우 즉시 전문상담교사 및 관련 기관과 연계해야 합니다.
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "① 상담 기록 입력",
    "② AI 분석 결과",
    "③ 유형별 상담 매뉴얼",
    "④ 대시보드",
    "⑤ 상담 시뮬레이션"
])


# =========================
# ① 상담 기록 입력
# =========================

with tab1:
    st.subheader("① 상담 기록 입력")

    sample_name = st.selectbox(
        "샘플 데이터 불러오기",
        ["직접 입력"] + list(SAMPLE_DATA.keys())
    )

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
        student_id = st.text_input("익명 학생 ID", value=selected["student_id"])

    with col2:
        grade = st.text_input("학년", value=selected["grade"])

    with col3:
        referral_source = st.text_input("상담 경로", value=selected["referral_source"])

    topic = st.text_input("상담 주제", value=selected["topic"])

    observation = st.text_area(
        "관찰 내용",
        value=selected["observation"],
        height=140
    )

    student_statement = st.text_area(
        "학생 발화",
        value=selected["student_statement"],
        height=120
    )

    risk_check = st.text_area(
        "위험 신호 체크",
        value=selected["risk_check"],
        height=80
    )

    teacher_memo = st.text_area(
        "교사 메모",
        value=selected["teacher_memo"],
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

    col_a, col_b = st.columns(2)

    with col_a:
        if st.button("AI 분석하기", use_container_width=True):
            prompt = build_prompt(current_data)

            with st.spinner("AI가 상담 기록을 분석하고 있습니다..."):
                try:
                    result_text = analyze_with_openai(prompt)
                    result_json = parse_json_safely(result_text)

                    st.session_state["last_input"] = current_data
                    st.session_state["last_result_text"] = result_text
                    st.session_state["last_result_json"] = result_json

                    st.success("AI 분석이 완료되었습니다. ② AI 분석 결과 탭에서 확인하세요.")
                except Exception as e:
                    st.error(f"분석 중 오류가 발생했습니다: {e}")

    with col_b:
        if st.button("프롬프트만 확인하기", use_container_width=True):
            prompt = build_prompt(current_data)
            st.code(prompt, language="text")


# =========================
# ② AI 분석 결과
# =========================

with tab2:
    st.subheader("② AI 분석 결과")

    result_json = st.session_state.get("last_result_json")
    result_text = st.session_state.get("last_result_text")
    last_input = st.session_state.get("last_input")

    if not result_text:
        st.info("아직 분석 결과가 없습니다. ① 상담 기록 입력 탭에서 AI 분석하기를 눌러주세요.")
    else:
        if result_json:
            col1, col2, col3 = st.columns(3)

            col1.metric("추정 학생 유형", result_json.get("추정학생유형", ""))
            col2.metric("위험도", result_json.get("위험도", ""))
            col3.metric("전문기관 연계", result_json.get("전문기관연계필요", ""))

            st.markdown("### 분석 상세")

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

            if st.button("분석 결과 CSV 저장"):
                save_result(last_input, result_json, result_text)
                st.success("저장 완료: counsel_results.csv 파일이 생성/업데이트되었습니다.")

        else:
            st.warning("AI 응답이 JSON으로 깔끔하게 변환되지 않았습니다. 원문을 확인하세요.")
            st.code(result_text, language="text")


# =========================
# ③ 유형별 상담 매뉴얼
# =========================

with tab3:
    st.subheader("③ 유형별 상담 매뉴얼")

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
# ④ 대시보드
# =========================

with tab4:
    st.subheader("④ 상담 대시보드")

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

# =========================
# ⑤ 상담 시뮬레이션
# =========================

with tab5:
    st.subheader("⑤ 상담 시뮬레이션")

    st.write("AI가 학생 역할을 하고, 사용자는 교사 역할로 상담 대화를 연습합니다.")

    sim_col1, sim_col2 = st.columns(2)

    with sim_col1:
        sim_grade = st.text_input("시뮬레이션 학생 학년", value="중학교 3학년")
        sim_type = st.selectbox(
            "시뮬레이션 학생 유형",
            list(TYPE_MANUAL.keys()),
            key="sim_type"
        )

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

    if st.button("시뮬레이션 시작"):
        st.session_state["sim_profile"] = {
            "grade": sim_grade,
            "type": sim_type,
            "topic": sim_topic,
            "personality": sim_personality,
            "background": sim_background
        }

        st.session_state["sim_messages"] = [
            {
                "role": "assistant",
                "content": "선생님... 무슨 이야기부터 해야 할지 잘 모르겠어요."
            }
        ]

        if "sim_feedback" in st.session_state:
            del st.session_state["sim_feedback"]

    if st.button("대화 초기화"):
        st.session_state["sim_messages"] = []
        if "sim_feedback" in st.session_state:
            del st.session_state["sim_feedback"]

    st.markdown("---")

    for message in st.session_state["sim_messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if "sim_profile" not in st.session_state:
        st.info("먼저 학생 정보를 설정한 뒤, '시뮬레이션 시작' 버튼을 눌러주세요.")
        user_input = None
    else:
        user_input = st.chat_input("교사로서 학생에게 상담 질문을 입력하세요.")

    if user_input:
        st.session_state["sim_messages"].append(
            {"role": "user", "content": user_input}
        )

        profile = st.session_state.get("sim_profile", {
            "grade": sim_grade,
            "type": sim_type,
            "topic": sim_topic,
            "personality": sim_personality,
            "background": sim_background
        })

        conversation_text = ""
        for msg in st.session_state["sim_messages"]:
            speaker = "교사" if msg["role"] == "user" else "학생"
            conversation_text += f"{speaker}: {msg['content']}\n"

        student_prompt = f"""
너는 학생 상담 시뮬레이션에서 '학생 역할'을 맡는다.
사용자는 교사 역할이다.

[학생 정보]
- 학년: {profile["grade"]}
- 학생 유형: {profile["type"]}
- 상담 주제: {profile["topic"]}
- 학생 성향: {profile["personality"]}
- 배경 상황: {profile["background"]}

[역할 지침]
1. 너는 AI 상담사가 아니라 학생이다.
2. 교사를 평가하거나 조언하지 말고, 학생처럼 자연스럽게 답하라.
3. 한 번에 너무 많은 정보를 말하지 말고, 실제 학생처럼 조금씩 감정을 드러내라.
4. 학생 유형과 배경 상황에 맞게 반응하라.
5. 자해, 자살, 학대, 폭력 피해 등 위기 신호가 설정된 경우에는 교사가 확인할 수 있도록 간접적 신호를 드러낼 수 있다.
6. 답변은 1~4문장 정도로 짧게 하라.

[지금까지의 대화]
{conversation_text}

마지막 교사의 말에 대해 학생 입장에서 답하라.
"""

        try:
            response = client.responses.create(
                model="gpt-4.1-mini",
                input=student_prompt
            )

            ai_reply = response.output_text

            st.session_state["sim_messages"].append(
                {"role": "assistant", "content": ai_reply}
            )

            st.rerun()

        except Exception as e:
            st.error(f"학생 응답 생성 중 오류가 발생했습니다: {e}")

    st.markdown("---")

    if st.button("상담 피드백 받기"):
        if len(st.session_state["sim_messages"]) < 3:
            st.warning("상담 대화가 너무 짧습니다. 최소 2~3회 이상 대화한 뒤 피드백을 받아보세요.")
        else:
            profile = st.session_state.get("sim_profile", {
                "grade": sim_grade,
                "type": sim_type,
                "topic": sim_topic,
                "personality": sim_personality,
                "background": sim_background
            })

            conversation_text = ""
            for msg in st.session_state["sim_messages"]:
                speaker = "교사" if msg["role"] == "user" else "학생"
                conversation_text += f"{speaker}: {msg['content']}\n"

            feedback_prompt = f"""
너는 교사 상담 훈련을 돕는 슈퍼바이저다.
아래 상담 시뮬레이션 대화를 보고 교사의 상담 역량을 피드백하라.

[학생 정보]
- 학년: {profile["grade"]}
- 학생 유형: {profile["type"]}
- 상담 주제: {profile["topic"]}
- 학생 성향: {profile["personality"]}
- 배경 상황: {profile["background"]}

[상담 대화]
{conversation_text}

[평가 기준]
1. 공감 표현이 있었는가?
2. 학생의 감정을 충분히 탐색했는가?
3. 닫힌 질문보다 열린 질문을 사용했는가?
4. 해결책을 너무 빨리 제시하지 않았는가?
5. 위험 신호 확인이 필요한 경우 적절히 확인했는가?
6. 학생에게 부담을 주지 않는 언어를 사용했는가?
7. 다음 상담에서 이어갈 질문이 명확한가?

아래 형식으로 출력하라.

## 종합 피드백
-

## 잘한 점
-

## 보완할 점
-

## 교사가 사용한 질문 분석
-

## 다음 상담에서 해볼 질문 3개
1.
2.
3.

## 학생에게 해줄 수 있는 피드백 문장
-

## 주의사항
-
"""

            try:
                response = client.responses.create(
                    model="gpt-4.1-mini",
                    input=feedback_prompt
                )

                st.session_state["sim_feedback"] = response.output_text

            except Exception as e:
                st.error(f"피드백 생성 중 오류가 발생했습니다: {e}")

    if "sim_feedback" in st.session_state:
        st.markdown("### 상담 피드백 결과")
        st.markdown(st.session_state["sim_feedback"])