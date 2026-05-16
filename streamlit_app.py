"""
🏫 교사 감정보호 & 갑질 방어 AI 플랫폼
========================================
Streamlit 기반 웹앱 (GitHub 무료 배포용)
"""

import streamlit as st
import pandas as pd
import json
import re
import sqlite3
from datetime import datetime, time as dtime
from pathlib import Path
from io import BytesIO
import time

# ============================================================
# 페이지 설정
# ============================================================
st.set_page_config(
    page_title="🛡️ 티쳐가드",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================================
# CSS 스타일
# ============================================================
def apply_styles():
    st.markdown("""
    <style>
    html, body, [class*="css"] {
        font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    .yellow-page {
        background: linear-gradient(160deg, #FFFDE7 0%, #FFF9C4 60%, #FFF176 100%);
        min-height: 80vh;
        padding: 40px 20px;
        border-radius: 20px;
        text-align: center;
    }
    .role-card {
        background: white;
        border-radius: 20px;
        padding: 35px 25px;
        text-align: center;
        box-shadow: 0 4px 20px rgba(0,0,0,0.10);
        border: 3px solid #FFF9C4;
        margin: 10px;
    }
    .emotion-char {
        font-size: 80px;
        text-align: center;
        display: block;
        animation: float 2s ease-in-out infinite;
    }
    @keyframes float {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-8px); }
    }
    .gauge-container {
        background: #f5f5f5;
        border-radius: 30px;
        height: 20px;
        margin: 8px 0;
        overflow: hidden;
    }
    .gauge-fill-1 { background: #4CAF50; width: 25%; height: 100%; border-radius: 30px; }
    .gauge-fill-2 { background: #FFC107; width: 50%; height: 100%; border-radius: 30px; }
    .gauge-fill-3 { background: #FF9800; width: 75%; height: 100%; border-radius: 30px; }
    .gauge-fill-4 { background: #F44336; width: 100%; height: 100%; border-radius: 30px; }
    .msg-bubble-parent {
        background: #E3F2FD;
        border-radius: 18px 18px 5px 18px;
        padding: 10px 16px;
        margin: 6px 0;
        max-width: 75%;
        float: right;
        clear: both;
        box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    }
    .msg-bubble-ai {
        background: #F3E5F5;
        border-radius: 18px 18px 18px 5px;
        padding: 10px 16px;
        margin: 6px 0;
        max-width: 75%;
        float: left;
        clear: both;
        box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    }
    .warning-box {
        background: #FFF8E1;
        border-left: 5px solid #FF9800;
        padding: 12px 16px;
        border-radius: 0 10px 10px 0;
        margin: 10px 0;
    }
    .danger-box {
        background: #FFEBEE;
        border-left: 5px solid #F44336;
        padding: 12px 16px;
        border-radius: 0 10px 10px 0;
        margin: 10px 0;
    }
    .badge-red    { background:#FFEBEE; color:#C62828; padding:3px 10px; border-radius:20px; font-size:12px; font-weight:700; margin:2px; display:inline-block; }
    .badge-orange { background:#FFF3E0; color:#E65100; padding:3px 10px; border-radius:20px; font-size:12px; font-weight:700; margin:2px; display:inline-block; }
    .badge-yellow { background:#FFFDE7; color:#F57F17; padding:3px 10px; border-radius:20px; font-size:12px; font-weight:700; margin:2px; display:inline-block; }
    .badge-green  { background:#E8F5E9; color:#2E7D32; padding:3px 10px; border-radius:20px; font-size:12px; font-weight:700; margin:2px; display:inline-block; }
    .archive-card {
        background: white;
        border-radius: 12px;
        padding: 14px 16px;
        margin: 8px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border-left: 4px solid #EF5350;
    }
    .stat-card {
        background: white;
        border-radius: 14px;
        padding: 18px;
        text-align: center;
        box-shadow: 0 2px 10px rgba(0,0,0,0.07);
    }
    .stat-num { font-size: 28px; font-weight: 700; }
    .stat-label { font-size: 12px; color: #888; margin-top: 4px; }
    </style>
    """, unsafe_allow_html=True)


# ============================================================
# 갑질 7유형 분류 딕셔너리 (확장판)
# ============================================================
ABUSE_TYPES = {
    "욕설/폭언": {
        "keywords": [
            "병신", "미친", "개새", "개같", "쓰레기", "한심", "새끼", "멍청",
            "지랄", "개소리", "닥쳐", "꺼져", "바보", "멍청이", "찐따",
            "시발", "씨발", "씨팔", "시팔", "ㅅㅂ", "ㅆㅂ", "tlqkf",
            "개년", "개놈", "존나", "뒤져", "뒤지", "엿같", "엿먹",
            "꼴통", "돌대가리", "썅", "개돼지", "미쳤냐", "돌았냐",
            "정신병", "정신나", "또라이", "싸가지", "버릇없",
            "그딴", "기가 막히", "어이가 없어", "분노 조절"
        ],
        "emoji": "🤬", "color": "#C62828", "badge": "badge-red", "severity": 4
    },
    "위협/협박": {
        "keywords": [
            "죽어", "고소", "경찰", "신고", "죽인다", "때린다", "고발",
            "법적", "소송", "변호사", "고소장", "처단", "응징", "망한다",
            "후회", "가만 안 둬", "가만두지", "두고봐", "두고 봐",
            "혼내", "망신", "뉴스", "기자", "언론", "민원", "교육청",
            "해고", "명예실추", "애아빠가", "아이아버지가", "클럽", "마약",
            "애아빠가 화가"
        ],
        "emoji": "⚠️", "color": "#E65100", "badge": "badge-red", "severity": 5
    },
    "모욕/비하": {
        "keywords": [
            "무능", "무식", "못난", "부끄러운", "형편없", "저능", "짜증",
            "답답", "황당", "어이없", "저급", "수준미달", "실망", "역겨",
            "한심하다", "쪽팔려", "창피", "수치", "민망", "부끄럽",
            "자격없", "자격 없", "실력없", "실력 없", "왜 선생이야",
            "생각이 짧", "교사 자질", "정신과", "명문대 나와",
            "발뺌", "배운 사람", "임신이 자랑", "명예실추"
        ],
        "emoji": "😤", "color": "#E65100", "badge": "badge-orange", "severity": 3
    },
    "강압/명령": {
        "keywords": [
            "해야 한다", "꼭 해라", "절대 안 된다", "즉시", "지금 당장",
            "명령", "강요", "무조건", "당장", "빨리빨리", "왜 안 해",
            "하라고", "해라", "시키는대로", "말 들어", "말을 들어",
            "내 말대로", "요구한다", "요구사항", "반드시",
            "아이폰으로 바꿔", "사진 많이"
        ],
        "emoji": "👊", "color": "#F57F17", "badge": "badge-orange", "severity": 3
    },
    "반복민원": {
        "keywords": [
            "또 이런", "계속", "매번", "또다시", "자꾸", "전에도",
            "반복", "항상", "맨날", "몇 번을", "또", "다시 또",
            "이번이 몇번", "몇 번째", "지난번에도", "저번에도"
        ],
        "emoji": "🔁", "color": "#F57F17", "badge": "badge-yellow", "severity": 2
    },
    "사생활침해": {
        "keywords": [
            "밤에", "새벽에", "주말에", "휴일에", "쉬는날", "개인번호",
            "집에", "퇴근 후", "퇴근후", "수업 끝나고", "방과후에",
            "자정", "저녁에", "일요일", "토요일", "공휴일", "연휴",
            "개인 연락", "카카오", "문자로", "전화로 계속"
        ],
        "emoji": "🌙", "color": "#6A1B9A", "badge": "badge-yellow", "severity": 2
    },
    "부당요구": {
        "keywords": [
            "성적 올려", "등급 바꿔", "특별히", "예외로", "특혜", "봐주세요",
            "조정해", "올려달라", "고쳐달라", "바꿔달라", "우리 애만",
            "우리 아이만", "점수 올려", "점수 바꿔", "재채점", "왜 우리 애가",
            "다른 애는", "불공평", "차별", "편애"
        ],
        "emoji": "🙏", "color": "#1565C0", "badge": "badge-yellow", "severity": 2
    }
}

# 변형어 패턴
VARIANT_PATTERNS = {
    "병신": ["ㅂㅅ", "병.신", "병~신", "병 신", "뵹신", "뼝신"],
    "미친": ["ㅁㅊ", "미.친", "미~친", "ㅁㅊㄴ", "미칀"],
    "개새": ["ㄱㅅ", "개.새", "개~새", "ㄱㅅㄲ"],
    "시발": ["ㅅㅂ", "ㅆㅂ", "씨발", "시.발", "시~발", "씨.발", "시팔", "씨팔", "십8"],
    "쓰레기": ["쓰렉", "ㅆㄹㄱ"],
    "멍청": ["멍.청", "멍~청"],
}


def blur_text(text: str) -> str:
    """욕설 단어를 ⬛로 블러처리"""
    result = text
    for abuse_type, data in ABUSE_TYPES.items():
        for keyword in data["keywords"]:
            if keyword in result:
                result = result.replace(keyword, "⬛" * len(keyword))
    for word, variants in VARIANT_PATTERNS.items():
        for variant in variants:
            if variant in result:
                result = result.replace(variant, "⬛" * len(variant))
    return result


def analyze_message(text: str) -> dict:
    """메시지 분석 — 갑질 7유형 + 심각도"""
    if not text or not text.strip():
        return {
            "is_profanity": False, "types_detected": [],
            "severity": 1, "emotion_level": 1,
            "etiquette_warning": None, "detected_keywords": []
        }

    detected_types = []
    detected_keywords = []
    max_severity = 1

    for abuse_type, data in ABUSE_TYPES.items():
        for keyword in data["keywords"]:
            if keyword in text:
                if abuse_type not in detected_types:
                    detected_types.append(abuse_type)
                detected_keywords.append(keyword)
                max_severity = max(max_severity, data["severity"])

    # 변형어 탐지
    for word, variants in VARIANT_PATTERNS.items():
        for variant in variants:
            if variant in text:
                if "욕설/폭언" not in detected_types:
                    detected_types.append("욕설/폭언")
                detected_keywords.append(f"{variant}(변형)")
                max_severity = max(max_severity, 4)

    # 강도 보정
    for w in ["진짜", "정말", "완전", "너무", "엄청"]:
        if w in text and max_severity > 1:
            max_severity = min(max_severity + 1, 5)

    # 감정 레벨 (1~4)
    if max_severity >= 5:   emotion_level = 4
    elif max_severity >= 4: emotion_level = 3
    elif max_severity >= 2: emotion_level = 2
    else:                   emotion_level = 1

    is_profanity = len(detected_types) > 0

    etiquette_warning = None
    if is_profanity:
        if emotion_level == 4:
            etiquette_warning = "🚨 이 메시지는 심각한 위협 표현을 포함합니다. 전송 시 교권보호위원회에 자동 신고될 수 있습니다."
        elif emotion_level == 3:
            etiquette_warning = "⚠️ 상대방에게 상처를 줄 수 있는 표현이 포함되어 있어요. 조금 더 부드럽게 표현해볼까요?"
        else:
            etiquette_warning = "💛 상대방이 불쾌하게 느낄 수 있는 표현이 있어요. 건강한 소통을 위해 표현을 바꿔보세요."

    return {
        "is_profanity": is_profanity,
        "types_detected": list(dict.fromkeys(detected_types)),
        "severity": max_severity,
        "emotion_level": emotion_level,
        "etiquette_warning": etiquette_warning,
        "detected_keywords": list(dict.fromkeys(detected_keywords))
    }


def get_emotion_info(level: int) -> dict:
    """감정 레벨 → 캐릭터/색상/라벨"""
    info = {
        1: {"char": "😊", "label": "정상", "color": "#4CAF50", "bg": "#E8F5E9",
            "gauge": "gauge-fill-1", "desc": "학부모와의 대화가 건강하게 이루어지고 있어요!"},
        2: {"char": "😐", "label": "주의", "color": "#FFC107", "bg": "#FFFDE7",
            "gauge": "gauge-fill-2", "desc": "약간의 부정적 표현이 감지됩니다. 주의 깊게 모니터링하세요."},
        3: {"char": "😟", "label": "경고", "color": "#FF9800", "bg": "#FFF3E0",
            "gauge": "gauge-fill-3", "desc": "명백한 부적절 표현이 탐지되었습니다. 기록을 보관하세요."},
        4: {"char": "😡", "label": "위험", "color": "#F44336", "bg": "#FFEBEE",
            "gauge": "gauge-fill-4", "desc": "심각한 폭언/위협이 탐지되었습니다! 즉시 조치가 필요합니다."},
    }
    return info.get(level, info[1])


def is_after_hours() -> bool:
    now = datetime.now().time()
    return now >= dtime(18, 0) or now < dtime(7, 0)


def get_auto_response(analysis: dict) -> str:
    if is_after_hours():
        return ("🌙 안녕하세요. 현재 운영 시간(07:00~18:00)이 아닙니다.\n"
                "업무 시간 내에 답변 드리겠습니다. 긴급한 경우 학교 대표번호로 연락 부탁드립니다.")
    if analysis["is_profanity"]:
        if analysis["emotion_level"] >= 4:
            return "⚠️ 전송하신 메시지에 부적절한 표현이 포함되어 정상적으로 전달되지 않았습니다. 적절한 표현으로 다시 작성해 주세요."
        return "💛 메시지 잘 받았습니다. 좀 더 건설적인 방향으로 대화해 주시면 더 빠르게 도움을 드릴 수 있습니다."
    return "✅ 메시지 잘 받았습니다. 확인 후 빠른 시일 내에 연락드리겠습니다."


# ============================================================
# 세션 상태 초기화
# ============================================================
def init_session():
    defaults = {
        "role": None,
        "user_id": None,
        "chat_messages": [],
        "archive": [],
        "blocked_users": set(),
        "current_emotion": 1,
        "stats": {"total": 0, "profanity": 0,
                  "types": {t: 0 for t in ABUSE_TYPES.keys()}}
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ============================================================
# 페이지 1: 홈
# ============================================================
def page_home():
    st.markdown("""
    <div class="yellow-page">
        <div style="font-size:72px; margin-bottom:10px;">🛡️</div>
        <h1 style="font-size:32px; font-weight:800; color:#1a1a2e; margin-bottom:6px;">
            티쳐가드 (TeacherGuard)
        </h1>
        <p style="font-size:16px; color:#555; margin-bottom:30px;">
            선생님을 지키는 AI · 건강한 소통을 위한 스마트 필터
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 💡 역할을 선택해주세요")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class="role-card">
            <div style="font-size:60px;">👩‍🏫</div>
            <div style="font-size:22px; font-weight:700; margin:8px 0;">교사</div>
            <div style="font-size:13px; color:#666; line-height:1.6;">
                학부모 메시지 실시간 모니터링<br>
                갑질 유형 분석 · 보관함 · 신고서 생성
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("👩‍🏫 교사로 시작하기 →", key="btn_teacher",
                     use_container_width=True, type="primary"):
            st.session_state.role = "teacher"
            st.session_state.user_id = "teacher_001"
            st.rerun()

    with col2:
        st.markdown("""
        <div class="role-card">
            <div style="font-size:60px;">👨‍👩‍👧</div>
            <div style="font-size:22px; font-weight:700; margin:8px 0;">학부모</div>
            <div style="font-size:13px; color:#666; line-height:1.6;">
                교사에게 메시지 보내기<br>
                AI 에티켓 가이드 · 건강한 소통 연습
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("👨‍👩‍👧 학부모로 시작하기 →", key="btn_parent",
                     use_container_width=True):
            st.session_state.role = "parent"
            st.session_state.user_id = f"parent_{int(time.time()) % 10000:04d}"
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("🤔 이 플랫폼은 무엇인가요?"):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**🛡️ 교사 보호**\n\n부적절한 메시지를 실시간 감지하고 증거를 자동 보관합니다.")
        with c2:
            st.markdown("**💬 건강한 소통**\n\n학부모에게 전송 전 에티켓 가이드를 제공해 갈등을 예방합니다.")
        with c3:
            st.markdown("**📄 신고서 자동화**\n\n교권보호위원회 제출용 신고서를 자동으로 생성합니다.")


# ============================================================
# 페이지 2: 학부모 채팅
# ============================================================
def page_parent():
    col_h1, col_h2 = st.columns([4, 1])
    with col_h1:
        st.markdown(f"### 💬 학부모 채팅방")
        st.caption(f"ID: {st.session_state.user_id}  |  "
                   f"{'🌙 운영시간 외 (18:00 이후)' if is_after_hours() else '🟢 운영시간 중'}")
    with col_h2:
        if st.button("🚪 나가기"):
            st.session_state.role = None
            st.session_state.chat_messages = []
            st.rerun()

    if is_after_hours():
        st.warning("🌙 현재 운영 시간(07:00~18:00)이 아닙니다. 메시지는 기록되지만 자동응답이 전송됩니다.")

    st.info("💛 **학부모 AI 에티켓 가이드**: 전송 전에 AI가 메시지를 확인합니다. 건강한 소통을 함께 만들어요!")
    st.divider()

    # 채팅 히스토리
    if not st.session_state.chat_messages:
        st.markdown("""
        <div style="text-align:center; color:#bbb; padding:40px;">
            📭 아직 메시지가 없어요. 아래에서 메시지를 보내보세요!
        </div>
        """, unsafe_allow_html=True)
    else:
        for msg in st.session_state.chat_messages:
            _render_chat_message(msg)

    st.divider()
    st.markdown("#### ✏️ 메시지 작성")
    user_input = st.text_area(
        "메시지 입력",
        placeholder="예) 안녕하세요. 오늘 수업에서 아이가 어려워했던 부분을 여쭤보고 싶습니다.",
        height=100, key="parent_input", label_visibility="collapsed"
    )

    # 실시간 분석
    if user_input:
        analysis = analyze_message(user_input)
        if analysis["is_profanity"]:
            emotion = get_emotion_info(analysis["emotion_level"])
            box_class = "danger-box" if analysis["emotion_level"] >= 3 else "warning-box"
            st.markdown(f"""
            <div class="{box_class}">
                <b>{emotion['char']} 전송 전 경고</b><br>
                {analysis['etiquette_warning']}
            </div>
            """, unsafe_allow_html=True)
            if analysis["detected_keywords"]:
                kw_html = " ".join([f'<span class="badge-red">{kw}</span>'
                                    for kw in analysis["detected_keywords"][:6]])
                st.markdown(f"**탐지된 표현:** {kw_html}", unsafe_allow_html=True)

    col_b1, col_b2 = st.columns([3, 1])
    with col_b1:
        if st.button("📤 전송", key="send_msg", use_container_width=True, type="primary"):
            if user_input.strip():
                _send_parent_message(user_input.strip())
                st.rerun()
    with col_b2:
        if st.button("🗑️ 지우기", key="clear_msg", use_container_width=True):
            st.rerun()


def _render_chat_message(msg: dict):
    ts = msg.get("timestamp", "")
    if msg["role"] == "parent":
        blurred = msg.get("blurred_text", msg["text"])
        emotion_info = get_emotion_info(msg.get("emotion_level", 1))
        blocked = msg.get("blocked", False)
        if blocked:
            st.markdown(f"""
            <div style="text-align:right; margin:8px 0;">
                <span style="font-size:11px; color:#999;">{ts}</span><br>
                <div style="display:inline-block; background:#FFEBEE; border:2px dashed #EF5350;
                     border-radius:12px; padding:10px 16px; max-width:70%;">
                    🚫 <i>이 메시지는 부적절한 표현으로 차단되었습니다.</i>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="text-align:right; margin:8px 0;">
                <span style="font-size:11px; color:#999;">{ts} &nbsp; {emotion_info['char']}</span><br>
                <div class="msg-bubble-parent" style="display:inline-block; text-align:left;">
                    {blurred}
                </div>
            </div>
            """, unsafe_allow_html=True)
    elif msg["role"] == "ai":
        st.markdown(f"""
        <div style="text-align:left; margin:8px 0;">
            <span style="font-size:11px; color:#999;">🤖 AI 응답 &nbsp; {ts}</span><br>
            <div class="msg-bubble-ai" style="display:inline-block;">
                {msg["text"]}
            </div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("<div style='clear:both;'></div>", unsafe_allow_html=True)


def _send_parent_message(text: str):
    analysis = analyze_message(text)
    now = datetime.now().strftime("%H:%M")
    blurred = blur_text(text) if analysis["is_profanity"] else text
    blocked = analysis["emotion_level"] >= 4

    msg = {
        "role": "parent",
        "text": text,
        "blurred_text": blurred,
        "blocked": blocked,
        "analysis": analysis,
        "emotion_level": analysis["emotion_level"],
        "timestamp": now,
        "user_id": st.session_state.user_id
    }
    st.session_state.chat_messages.append(msg)

    if analysis["is_profanity"]:
        st.session_state.archive.append({**msg, "archived_at": datetime.now().isoformat()})
        st.session_state.stats["profanity"] += 1
        for t in analysis["types_detected"]:
            if t in st.session_state.stats["types"]:
                st.session_state.stats["types"][t] += 1

    st.session_state.stats["total"] += 1

    recent = st.session_state.chat_messages[-5:]
    levels = [m.get("emotion_level", 1) for m in recent if m["role"] == "parent"]
    st.session_state.current_emotion = max(levels) if levels else 1

    st.session_state.chat_messages.append({
        "role": "ai",
        "text": get_auto_response(analysis),
        "timestamp": now
    })


# ============================================================
# 페이지 3: 교사 대시보드
# ============================================================
def page_teacher():
    col_h1, col_h2 = st.columns([4, 1])
    with col_h1:
        st.markdown("### 👩‍🏫 교사 대시보드")
        st.caption(f"ID: {st.session_state.user_id}  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    with col_h2:
        if st.button("🚪 나가기"):
            st.session_state.role = None
            st.rerun()

    tab1, tab2, tab3, tab4 = st.tabs(
        ["🌡️ 실시간 모니터", "📥 보관함", "📊 통계/리포트", "📄 신고서 생성"])

    with tab1: _tab_monitor()
    with tab2: _tab_archive()
    with tab3: _tab_statistics()
    with tab4: _tab_report()


def _tab_monitor():
    emotion_level = st.session_state.current_emotion
    emotion = get_emotion_info(emotion_level)
    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown(f"""
        <div style="background:{emotion['bg']}; border-radius:20px; padding:20px; text-align:center;">
            <div class="emotion-char">{emotion['char']}</div>
            <div style="font-size:22px; font-weight:700; color:{emotion['color']}; margin:8px 0;">
                {emotion['label']}
            </div>
            <div class="gauge-container">
                <div class="{emotion['gauge']}"></div>
            </div>
            <div style="font-size:11px; color:#888; margin-top:8px;">감정 온도 Lv.{emotion_level}/4</div>
            <div style="font-size:12px; color:#555; margin-top:10px; line-height:1.5;">
                {emotion['desc']}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("#### 📨 실시간 메시지 현황")
        stats = st.session_state.stats
        c1, c2, c3 = st.columns(3)
        rate = round(stats['profanity'] / stats['total'] * 100, 1) if stats['total'] > 0 else 0
        with c1:
            st.markdown(f'<div class="stat-card"><div class="stat-num" style="color:#1565C0;">{stats["total"]}</div><div class="stat-label">전체 메시지</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="stat-card"><div class="stat-num" style="color:#C62828;">{stats["profanity"]}</div><div class="stat-label">부적절 메시지</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="stat-card"><div class="stat-num" style="color:#E65100;">{rate}%</div><div class="stat-label">부적절 비율</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### 🏷️ 갑질 유형 현황")
        types = stats["types"]
        type_data = [(t, c) for t, c in types.items() if c > 0]
        if type_data:
            for t_name, t_count in sorted(type_data, key=lambda x: -x[1]):
                info = ABUSE_TYPES[t_name]
                pct = int(t_count / stats['profanity'] * 100) if stats['profanity'] > 0 else 0
                st.markdown(f"""
                <div style="display:flex; align-items:center; gap:8px; margin:4px 0;">
                    <span style="width:90px; font-size:12px;">{info['emoji']} {t_name}</span>
                    <div style="flex:1; background:#f0f0f0; border-radius:10px; height:14px; overflow:hidden;">
                        <div style="background:{info['color']}; width:{pct}%; height:100%; border-radius:10px;"></div>
                    </div>
                    <span style="font-size:12px; width:35px; text-align:right;">{t_count}건</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("✅ 아직 탐지된 갑질 유형이 없습니다!")

        st.markdown("#### 📋 최근 메시지")
        recent_msgs = [m for m in st.session_state.chat_messages if m["role"] == "parent"][-5:]
        if recent_msgs:
            for msg in reversed(recent_msgs):
                e = get_emotion_info(msg.get("emotion_level", 1))
                types_str = ", ".join(msg["analysis"].get("types_detected", []))
                st.markdown(f"""
                <div style="background:white; border-radius:10px; padding:10px 14px;
                     margin:4px 0; border-left:4px solid {e['color']}; box-shadow:0 1px 4px rgba(0,0,0,0.07);">
                    <span style="font-size:18px;">{e['char']}</span>
                    <span style="font-size:13px; margin-left:8px;">{msg['text'][:60]}{'...' if len(msg['text'])>60 else ''}</span>
                    <span style="float:right; font-size:11px; color:#aaa;">{msg.get('timestamp','')}</span>
                    {"<br><small style='color:#E65100;'>⚠️ " + types_str + "</small>" if types_str else ""}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("📭 아직 수신된 메시지가 없습니다.")

    if st.button("🔄 새로고침", key="refresh_monitor"):
        st.rerun()


def _tab_archive():
    st.markdown("#### 📥 갑질 메시지 보관함")
    st.caption("블러처리 없이 원문이 저장됩니다. 교권보호위원회 제출 증거로 활용하세요.")
    archive = st.session_state.archive
    if not archive:
        st.info("📭 저장된 메시지가 없습니다. 부적절한 메시지가 탐지되면 자동 보관됩니다.")
        return

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filter_type = st.selectbox("유형 필터", ["전체"] + list(ABUSE_TYPES.keys()))
    with col_f2:
        sort_order = st.selectbox("정렬", ["최신순", "심각도순"])

    filtered = archive if filter_type == "전체" else [
        m for m in archive if filter_type in m["analysis"].get("types_detected", [])]
    if sort_order == "심각도순":
        filtered = sorted(filtered, key=lambda x: -x["analysis"]["severity"])

    st.markdown(f"**총 {len(filtered)}건** 보관 중")
    for i, msg in enumerate(reversed(filtered)):
        analysis = msg["analysis"]
        e = get_emotion_info(msg.get("emotion_level", 1))
        types_str = " ".join([
            f'<span class="{ABUSE_TYPES[t]["badge"]}">{ABUSE_TYPES[t]["emoji"]} {t}</span>'
            for t in analysis.get("types_detected", []) if t in ABUSE_TYPES
        ])
        st.markdown(f"""
        <div class="archive-card">
            <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
                <span>{e['char']} <b style="color:{e['color']};">{e['label']}</b></span>
                <span style="font-size:11px; color:#aaa;">{msg.get('timestamp','')} · {msg.get('user_id','')}</span>
            </div>
            <div style="font-size:14px; color:#1a1a2e; margin-bottom:8px; padding:8px;
                 background:#fff8f8; border-radius:8px;">"{msg['text']}"</div>
            <div>{types_str}</div>
        </div>
        """, unsafe_allow_html=True)

        ca, cb = st.columns(2)
        with ca:
            if st.button(f"🚫 차단", key=f"block_{i}_{msg.get('timestamp','')}"):
                st.session_state.blocked_users.add(msg.get("user_id", ""))
                st.success("✅ 차단 완료!")
        with cb:
            if st.button(f"📤 신고서 포함", key=f"report_{i}_{msg.get('timestamp','')}"):
                st.success("✅ 신고서 목록에 추가!")


def _tab_statistics():
    st.markdown("#### 📊 분석 통계")
    stats = st.session_state.stats
    archive = st.session_state.archive
    rate = round(stats['profanity'] / stats['total'] * 100, 1) if stats['total'] > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("전체 메시지", stats['total'])
    with c2: st.metric("부적절 메시지", stats['profanity'])
    with c3: st.metric("부적절 비율", f"{rate}%")
    with c4: st.metric("차단된 학부모", len(st.session_state.blocked_users))

    st.divider()
    st.markdown("#### 🏷️ 갑질 유형 분포")
    type_data = {t: c for t, c in stats["types"].items() if c > 0}
    if type_data:
        df = pd.DataFrame(list(type_data.items()), columns=["유형", "건수"])
        st.bar_chart(df.set_index("유형"))
    else:
        st.info("아직 탐지된 갑질 유형이 없습니다.")

    st.divider()
    st.markdown("#### 🌡️ 감정 레벨 분포")
    if archive:
        level_counts = {1: 0, 2: 0, 3: 0, 4: 0}
        for msg in archive:
            lvl = msg.get("emotion_level", 1)
            level_counts[lvl] = level_counts.get(lvl, 0) + 1
        df2 = pd.DataFrame([
            {"레벨": "🟢 정상", "건수": level_counts[1]},
            {"레벨": "🟡 주의", "건수": level_counts[2]},
            {"레벨": "🟠 경고", "건수": level_counts[3]},
            {"레벨": "🔴 위험", "건수": level_counts[4]},
        ])
        st.bar_chart(df2.set_index("레벨"))
    else:
        st.info("아직 데이터가 없습니다.")

    st.divider()
    st.markdown("#### 🤖 AI 자동 대화 요약")
    if archive:
        profanity_types = [t for m in archive for t in m["analysis"].get("types_detected", [])]
        top_type = max(set(profanity_types), key=profanity_types.count) if profanity_types else "없음"
        max_level = max([m.get("emotion_level", 1) for m in archive])
        e = get_emotion_info(max_level)
        st.markdown(f"""
📋 **현재까지 대화 요약**

- 총 **{stats['total']}건** 메시지 수신, 그 중 **{stats['profanity']}건**이 부적절
- 가장 많은 갑질 유형: **{top_type}**
- 최고 감정 레벨: {e['char']} **{e['label']}**
- 차단된 학부모: **{len(st.session_state.blocked_users)}명**

{"⚠️ 즉각적인 조치 및 교권보호위원회 신고를 권장합니다." if max_level >= 4 else "✅ 지속적인 모니터링을 권장합니다."}
        """)
    else:
        st.info("아직 분석된 메시지가 없습니다.")


def _tab_report():
    st.markdown("#### 📄 교권보호위원회 신고서 자동 생성")
    st.info("보관함의 메시지를 기반으로 신고서를 자동 생성합니다.")
    archive = st.session_state.archive
    if not archive:
        st.warning("⚠️ 보관함에 저장된 메시지가 없습니다.")
        return

    with st.form("report_form"):
        st.markdown("**👩‍🏫 신고인 정보**")
        c1, c2 = st.columns(2)
        with c1:
            teacher_name = st.text_input("교사 성명", placeholder="홍길동")
            school_name  = st.text_input("학교명", placeholder="○○초등학교")
        with c2:
            teacher_grade   = st.text_input("담당 학년/반", placeholder="3학년 2반")
            incident_date   = st.date_input("신고 날짜", datetime.now())
        st.markdown("**📝 신고 내용**")
        incident_summary = st.text_area(
            "사건 경위",
            value=_generate_incident_summary(archive),
            height=120
        )
        submitted = st.form_submit_button("📄 신고서 생성", type="primary", use_container_width=True)

    if submitted and teacher_name and school_name:
        report_text = _generate_report_text(
            teacher_name, school_name, teacher_grade,
            str(incident_date), incident_summary, archive
        )
        st.success("✅ 신고서가 생성되었습니다!")
        st.markdown("---")
        st.markdown(f"```\n{report_text}\n```")
        st.download_button(
            "⬇️ 신고서 다운로드 (.txt)",
            data=report_text.encode("utf-8"),
            file_name=f"교권침해_신고서_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain",
            use_container_width=True
        )


def _generate_incident_summary(archive):
    if not archive: return ""
    types_all = [t for m in archive for t in m["analysis"].get("types_detected", [])]
    top_types = list(dict.fromkeys(types_all))[:3]
    return (f"학부모로부터 총 {len(archive)}건의 부적절한 메시지를 수신하였습니다. "
            f"주요 유형은 {', '.join(top_types)}이며, 지속적인 민원으로 "
            f"교사의 정상적인 업무 수행에 심각한 지장을 초래하고 있습니다.")


def _generate_report_text(teacher_name, school, grade, date, summary, archive):
    msgs_text = "\n".join([
        f"  [{i+1}] {m.get('timestamp','')} | "
        f"{'/'.join(m['analysis'].get('types_detected',[]))} | "
        f"\"{m['text']}\""
        for i, m in enumerate(archive[:10])
    ])
    extra = f"  ... (외 {len(archive)-10}건)" if len(archive) > 10 else ""
    return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
         교 권 침 해 신 고 서
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

■ 신고인 정보
  성  명 : {teacher_name}
  소속학교 : {school}
  담당학급 : {grade}
  신고일자 : {date}

■ 피해 내용 요약
  {summary}

■ 증거 메시지 목록 (총 {len(archive)}건)
{msgs_text}
{extra}

■ AI 분석 결과
  총 수신 메시지 : {st.session_state.stats['total']}건
  부적절 메시지 : {st.session_state.stats['profanity']}건
  최고 위험 레벨 : {get_emotion_info(st.session_state.current_emotion)['label']}

■ 요청 사항
  첨부된 메시지 기록을 바탕으로 교권침해 사실을 확인하고
  필요한 조치를 취해 주시기 바랍니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  * 본 신고서는 티쳐가드(TeacherGuard) AI 플랫폼에 의해 자동 생성되었습니다.
  * 생성 일시 : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


# ============================================================
# 메인
# ============================================================
def main():
    apply_styles()
    init_session()
    role = st.session_state.role
    if role is None:
        page_home()
    elif role == "parent":
        page_parent()
    elif role == "teacher":
        page_teacher()


if __name__ == "__main__":
    main()
