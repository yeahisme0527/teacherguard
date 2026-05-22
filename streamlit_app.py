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
from datetime import datetime, time as dtime, timezone, timedelta
from pathlib import Path
from io import BytesIO
import time

import db          # Supabase 연동 (없으면 자동으로 session_state 폴백)
import hate_model  # kor_unsmile 혐오표현 탐지 (없으면 키워드 탐지로 폴백)
import schools     # NEIS 공공 API 기반 전국 학교 검색

# 한국 표준시(KST). Streamlit Cloud 서버는 UTC라서 시간 판정이 어긋남 → KST로 고정.
KST = timezone(timedelta(hours=9))


def now_kst() -> datetime:
    """항상 한국 시간 기준의 현재 시각을 반환."""
    return datetime.now(KST)

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
    [data-testid="stToolbar"] {visibility: hidden;}

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
    "멍청이": ["멍처이", "멍청ㅇ", "멍치이", "멍텅구리", "멍.청", "멍~청", "멍청"],
    "바보": ["ㅂㅂ", "바.보", "바~보", "바 보", "빠보", "바봐"],
    "닥쳐": ["닥.쳐", "닥~쳐", "닥처", "닥쳐라", "닥ㅊ"],
    "죽어": ["죽.어", "죽~어", "뒤져", "뒤지어", "뒤짐"],
    "꺼져": ["꺼.져", "꺼~져", "꺼지어", "꺼짐", "꺼저"],
    "찐따": ["찐.따", "찐~따", "찐다", "찐따새"],
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


def analyze_message(text: str, use_model: bool = False) -> dict:
    """메시지 분석 — 갑질 7유형 + 심각도.

    use_model=True 이면 kor_unsmile(HF Inference API)로 한 번 더 검사해
    키워드로 못 잡는 변형 욕설/혐오표현을 보완한다. (전송 시에만 사용)
    """
    if not text or not text.strip():
        return {
            "is_profanity": False, "types_detected": [],
            "severity": 1, "emotion_level": 1,
            "etiquette_warning": None, "detected_keywords": [],
            "model_used": False, "model_labels": []
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

    # AI 모델(kor_unsmile) 보강 — 키워드가 놓친 욕설/혐오 탐지
    model_used = False
    model_labels = []
    if use_model:
        model_result = hate_model.classify(text)
        if model_result is not None:
            model_used = True
            model_labels = model_result.get("labels", [])
            if model_result.get("profanity"):
                if "욕설/폭언" not in detected_types:
                    detected_types.append("욕설/폭언")
                detected_keywords.append("AI탐지:악플/욕설")
                max_severity = max(max_severity, 4)
            if model_result.get("hate"):
                if "모욕/비하" not in detected_types:
                    detected_types.append("모욕/비하")
                max_severity = max(max_severity, 3)
                for cat in model_result.get("hate_categories", []):
                    detected_keywords.append(f"AI탐지:{cat}")

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
        "detected_keywords": list(dict.fromkeys(detected_keywords)),
        "model_used": model_used,
        "model_labels": model_labels,
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
    now = now_kst().time()
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
        # 인증
        "auth_user": None,         # {"user_id", "email", "display_name"} 또는 None
        "auth_mode": "login",       # "login" or "signup"
        # 앱 상태
        "role": None,
        "user_id": None,
        "chat_messages": [],
        "archive": [],
        "blocked_users": set(),
        "current_emotion": 1,
        "stats": {"total": 0, "profanity": 0,
                  "types": {t: 0 for t in ABUSE_TYPES.keys()}},
        "db_loaded": False,         # 로그인 직후 DB → session_state 1회 동기화 플래그
        "school_selected": False,   # 교사 학교 선택 완료 여부
        "teacher_room_id": None,    # 학부모가 연결된 교사 user_id
        "teacher_info": {},         # 연결된 교사 정보 {"display_name", "school_name", ...}
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _hydrate_from_db():
    """로그인 직후 DB에서 채팅/보관함/차단 목록을 한 번 불러와 session_state에 채운다.
    DB 미설정/실패 시에는 그대로 빈 상태(또는 기존 session_state) 사용.
    """
    if st.session_state.get("db_loaded"):
        return
    if not db.is_enabled():
        st.session_state.db_loaded = True
        return

    # 교사는 자신의 방(room_id = user_id) 메시지 로드
    _uid = (st.session_state.auth_user or {}).get("user_id", "")
    _fetch_room = getattr(db, "fetch_room_messages", None)
    if _fetch_room and _uid:
        ok_msgs, msgs = _fetch_room(_uid, limit=200)
    else:
        ok_msgs, msgs = db.fetch_messages(limit=200)  # 구버전 폴백
    if ok_msgs and msgs:
        st.session_state.chat_messages = msgs

    ok_arc, arc = db.fetch_archive()
    if ok_arc and arc:
        st.session_state.archive = arc
        # 통계 재집계
        stats = {"total": len(msgs) if ok_msgs else 0,
                 "profanity": len(arc),
                 "types": {t: 0 for t in ABUSE_TYPES.keys()}}
        for m in arc:
            for t in m.get("analysis", {}).get("types_detected", []):
                if t in stats["types"]:
                    stats["types"][t] += 1
        st.session_state.stats = stats
        levels = [m.get("emotion_level", 1) for m in (msgs or [])
                  if m.get("role") == "parent"][-5:]
        st.session_state.current_emotion = max(levels) if levels else 1

    user = st.session_state.auth_user or {}
    if user.get("user_id"):
        ok_b, blocked = db.fetch_blocked_users(user["user_id"])
        if ok_b:
            st.session_state.blocked_users = blocked

        # 프로필(학교 정보) 로드
        fetch_profile_fn = getattr(db, "fetch_profile", None)
        if fetch_profile_fn:
            try:
                ok_p, profile = fetch_profile_fn(user["user_id"])
            except Exception:
                ok_p, profile = False, {}
            if ok_p and profile:
                user = dict(user)
                user["school_region"] = profile.get("school_region") or ""
                user["school_type"]   = profile.get("school_type")   or ""
                user["school_name"]   = profile.get("school_name")   or ""
                st.session_state.auth_user = user
                # 이미 학교가 저장돼 있으면 선택 화면 건너뛰기
                if profile.get("school_name"):
                    st.session_state.school_selected = True

    st.session_state.db_loaded = True


# ============================================================
# 페이지 0: 로그인 / 회원가입
# ============================================================
def page_auth():
    st.markdown("""
    <div class="yellow-page">
        <div style="font-size:72px; margin-bottom:10px;">🛡️</div>
        <h1 style="font-size:30px; font-weight:800; color:#1a1a2e; margin-bottom:6px;">
            티쳐가드 (TeacherGuard)
        </h1>
        <p style="font-size:15px; color:#555; margin-bottom:10px;">
            선생님을 지키는 AI · 건강한 소통을 위한 스마트 필터
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if not db.is_enabled():
        st.warning(
            "⚠️ Supabase가 아직 설정되지 않았습니다. "
            "`SUPABASE_SETUP.md`를 참고해 `.streamlit/secrets.toml`에 키를 넣으면 "
            "데이터가 클라우드 DB에 저장됩니다. 지금은 **게스트 모드(로컬 세션)** 로 진행할 수 있어요."
        )
        if st.button("👤 게스트로 시작하기", type="primary", use_container_width=True):
            st.session_state.auth_user = {
                "user_id": f"guest_{int(time.time()) % 100000:05d}",
                "email": "guest@local",
                "display_name": "게스트",
            }
            st.session_state.db_loaded = True
            st.rerun()
        return

    tab_login, tab_signup = st.tabs(["🔑 로그인", "📝 회원가입"])

    with tab_login:
        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("이메일", key="login_email",
                                  placeholder="teacher@example.com")
            password = st.text_input("비밀번호", type="password", key="login_pw")
            submitted = st.form_submit_button("로그인", type="primary",
                                              use_container_width=True)
        if submitted:
            if not email or not password:
                st.error("이메일과 비밀번호를 모두 입력해주세요.")
            else:
                ok, data = db.sign_in(email.strip(), password)
                if ok:
                    st.session_state.auth_user = {
                        "user_id": data["user_id"],
                        "email": data["email"],
                        "display_name": data["email"].split("@")[0],
                    }
                    st.session_state.db_loaded = False  # 다음 렌더 때 hydrate
                    st.success("로그인 성공! 잠시만요...")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error(str(data))

    with tab_signup:
        with st.form("signup_form", clear_on_submit=False):
            name = st.text_input("표시 이름 (선택)", key="signup_name",
                                 placeholder="홍길동")
            email = st.text_input("이메일", key="signup_email",
                                  placeholder="teacher@example.com")
            password = st.text_input("비밀번호 (6자 이상)", type="password",
                                     key="signup_pw")
            submitted = st.form_submit_button("회원가입", type="primary",
                                              use_container_width=True)
        if submitted:
            if not email or not password:
                st.error("이메일과 비밀번호를 모두 입력해주세요.")
            elif len(password) < 6:
                st.error("비밀번호는 6자 이상이어야 합니다.")
            else:
                ok, msg = db.sign_up(email.strip(), password, name.strip())
                if ok:
                    st.success(msg + " 이제 [로그인] 탭에서 로그인해주세요.")
                else:
                    st.error(str(msg))

    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("🤔 회원가입이 꼭 필요한가요?"):
        st.markdown(
            "- 로그인하면 메시지/보관함/차단 목록이 **클라우드 DB에 자동 저장**되어, "
            "기기나 브라우저를 바꿔도 그대로 유지됩니다.\n"
            "- 교권보호위원회 신고서 생성 시 영구 기록이 증거로 활용됩니다.\n"
            "- DB 설정이 안 된 환경에서는 **게스트 모드**로 체험만 가능합니다."
        )


# ============================================================
# 페이지 1-P: 학부모 코드 입력 (교사 방 입장)
# ============================================================
def page_parent_connect() -> None:
    """학부모가 교사 초대코드를 입력해 해당 교사 방에 입장하는 화면."""
    st.markdown("""
    <div style="text-align:center; padding:30px 0 10px;">
        <div style="font-size:64px;">🔑</div>
        <h2 style="font-size:26px; font-weight:800; color:#1a1a2e; margin:8px 0 4px;">
            교사 초대코드 입력
        </h2>
        <p style="color:#666; font-size:14px;">
            담임·담당 선생님께 받은 <b>6자리 코드</b>를 입력하세요.<br>
            코드는 교사 대시보드에서 확인할 수 있습니다.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    code_input = st.text_input(
        "초대코드 (6자리)",
        placeholder="예: A1B2C3",
        max_chars=6,
        key="parent_invite_code",
    )
    code = (code_input or "").upper().strip()

    # 실시간 미리보기: 6자 입력되면 교사 조회
    teacher_preview = None
    if len(code) == 6 and db.is_enabled():
        with st.spinner("코드 확인 중..."):
            ok, teacher = db.fetch_teacher_by_code(code)
        if ok and teacher:
            teacher_preview = teacher
            school_str = ""
            if teacher.get("school_region") or teacher.get("school_name"):
                school_str = f"{teacher.get('school_region','')} {teacher.get('school_name','')}".strip()
            st.success(
                f"✅ **{teacher.get('display_name', '선생님')}** "
                f"{'(' + school_str + ')' if school_str else ''} 채팅방을 찾았어요!"
            )
        elif len(code) == 6:
            st.error("❌ 코드를 찾을 수 없습니다. 선생님께 다시 확인해주세요.")

    elif len(code) == 6 and not db.is_enabled():
        # 게스트 모드 — DB 없이 로컬로만
        teacher_preview = {
            "id": "guest_teacher",
            "display_name": "선생님(게스트)",
            "school_name": "",
        }
        st.info("⚪ 게스트 모드 — 코드 검증 없이 임시 입장합니다.")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button(
        "🚪 채팅방 입장",
        type="primary",
        use_container_width=True,
        disabled=(teacher_preview is None),
    ):
        st.session_state.teacher_room_id = teacher_preview["id"]
        st.session_state.teacher_info    = teacher_preview
        # 이 방의 기존 메시지 로드
        _fetch_room = getattr(db, "fetch_room_messages", None)
        if db.is_enabled() and teacher_preview["id"] != "guest_teacher" and _fetch_room:
            ok2, msgs = _fetch_room(teacher_preview["id"])
            if ok2:
                st.session_state.chat_messages = msgs
        st.rerun()


# ============================================================
# 페이지 1-A: 학교 선택 (교사 전용 — 첫 로그인 시 한 번)
# ============================================================
def _save_school(region: str, school_type: str, school_name: str) -> None:
    """학교 정보를 session_state 와 DB 에 저장."""
    user = dict(st.session_state.auth_user or {})
    user["school_region"] = region
    user["school_type"]   = school_type
    user["school_name"]   = school_name
    st.session_state.auth_user = user
    st.session_state.school_selected = True

    if db.is_enabled() and user.get("user_id"):
        db.update_profile(
            user["user_id"],
            school_region=region,
            school_type=school_type,
            school_name=school_name,
        )
    st.rerun()


def page_school_select() -> None:
    """교사가 처음 로그인할 때 자신의 학교를 선택하는 화면."""
    st.markdown("""
    <div style="text-align:center; padding:30px 0 10px;">
        <div style="font-size:64px;">🏫</div>
        <h2 style="font-size:26px; font-weight:800; color:#1a1a2e; margin:8px 0 4px;">
            내 학교 선택
        </h2>
        <p style="color:#666; font-size:14px;">
            선생님의 학교를 선택하면 교권보호 신고서에 자동으로 반영됩니다.<br>
            나중에 사이드바 → 학교 변경에서도 수정 가능합니다.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── 1단계: 지역 + 학교급 ────────────────────────────────────
    c1, c2 = st.columns(2)
    with c1:
        region = st.selectbox(
            "📍 시도 선택",
            options=["선택해주세요"] + schools.get_regions(),
            key="sch_region",
        )
    with c2:
        school_type = st.selectbox(
            "🏫 학교급 선택",
            options=["선택해주세요"] + schools.get_school_types(),
            key="sch_type",
        )

    school_name = ""

    # ── 2단계: 학교명 ───────────────────────────────────────────
    if region != "선택해주세요" and school_type != "선택해주세요":

        if school_type == "어린이집":
            st.info("어린이집은 공공 데이터 미지원 — 직접 입력해주세요.")
            school_name = st.text_input(
                "어린이집 이름", key="sch_name_manual",
                placeholder="예: 햇살어린이집"
            )

        elif schools.is_api_enabled():
            # NEIS API 사용 — 검색어로 필터링
            search_q = st.text_input(
                "🔍 학교명 검색",
                key="sch_search",
                placeholder="학교명 일부를 입력하세요 (예: 서울, 한국, 중앙)",
            )
            with st.spinner("학교 목록 불러오는 중..."):
                school_list = schools.search_schools(region, school_type, search_q)

            if school_list:
                selected = st.selectbox(
                    f"학교 선택 ({len(school_list):,}개 검색됨)",
                    options=["선택해주세요"] + school_list,
                    key="sch_name_api",
                )
                school_name = "" if selected == "선택해주세요" else selected
            else:
                if search_q:
                    st.warning("검색 결과가 없어요. 다른 검색어를 시도해보세요.")
                school_name = st.text_input(
                    "학교명 직접 입력",
                    key="sch_name_direct",
                    placeholder="예: 서울고등학교",
                )

        else:
            # API 키 없음 — 직접 입력
            st.markdown(
                "> 💡 **NEIS API 키를 등록하면** 학교 목록에서 바로 검색할 수 있어요.  \n"
                "> 등록 방법: [NEIS Open API](https://open.neis.go.kr/portal/guide/apiRegisterV2.do) → "
                "`secrets.toml` `[neis] key = \"...\"` 추가"
            )
            school_name = st.text_input(
                "학교명 직접 입력",
                key="sch_name_text",
                placeholder="예: 경기고등학교",
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 버튼 ────────────────────────────────────────────────────
    btn_save, btn_skip = st.columns([3, 2])
    with btn_save:
        can_save = bool(
            school_name.strip()
            and region != "선택해주세요"
            and school_type != "선택해주세요"
        )
        if st.button("✅ 저장하고 시작하기", type="primary",
                     use_container_width=True, disabled=not can_save):
            _save_school(region, school_type, school_name.strip())

    with btn_skip:
        if st.button("⏭️ 나중에 설정", use_container_width=True):
            st.session_state.school_selected = True
            st.rerun()


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

    # 연결 상태 한눈에 보기
    c1, c2 = st.columns(2)
    with c1:
        if db.is_enabled():
            st.success("🟢 DB 연결됨")
        else:
            st.info("⚪ 게스트 모드")
    with c2:
        if hate_model.is_enabled():
            st.success("🤖 AI 탐지 활성")
            err = st.session_state.get("_hf_last_error")
            if err:
                st.caption(f"⚠️ 마지막 API 오류: {err}")
        else:
            st.warning("🔑 AI 탐지 비활성")

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
            auth_user = st.session_state.get("auth_user") or {}
            st.session_state.user_id = auth_user.get("user_id", "teacher_001")
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
            auth_user = st.session_state.get("auth_user") or {}
            st.session_state.user_id = auth_user.get(
                "user_id", f"parent_{int(time.time()) % 10000:04d}"
            )
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
    # 연결된 교사 정보 배너
    t_info = st.session_state.get("teacher_info") or {}
    t_name = t_info.get("display_name", "선생님")
    t_school = t_info.get("school_name", "")
    banner_txt = f"🏫 **{t_school + ' ' if t_school else ''}{t_name}** 채팅방"
    st.info(banner_txt)

    col_h1, col_h2 = st.columns([4, 1])
    with col_h1:
        st.markdown("### 💬 학부모 채팅방")
        st.caption(f"{'🌙 운영시간 외 (18:00 이후)' if is_after_hours() else '🟢 운영시간 중'}")
    with col_h2:
        if st.button("🚪 나가기"):
            st.session_state.role = None
            st.session_state.teacher_room_id = None
            st.session_state.teacher_info = {}
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
        if st.button("🔄 새로고침", key="refresh_parent", use_container_width=True,
                     help="선생님의 새 답장을 불러옵니다."):
            _reload_messages_from_db()
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
            analysis = msg.get("analysis", {})
            model_badge = ""
            if analysis.get("model_used"):
                model_badge = ' &nbsp;<span style="background:#E8F5E9;color:#2E7D32;font-size:10px;padding:2px 6px;border-radius:10px;">🤖 AI</span>'
            st.markdown(f"""
            <div style="text-align:right; margin:8px 0;">
                <span style="font-size:11px; color:#999;">{ts} &nbsp; {emotion_info['char']}{model_badge}</span><br>
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
    elif msg["role"] == "teacher":
        st.markdown(f"""
        <div style="text-align:left; margin:8px 0;">
            <span style="font-size:11px; color:#999;">👩‍🏫 선생님 &nbsp; {ts}</span><br>
            <div style="display:inline-block; background:#E8F5E9;
                 border-radius:18px 18px 18px 5px; padding:10px 16px; max-width:75%;
                 box-shadow:0 1px 4px rgba(0,0,0,0.08);">
                {msg["text"]}
            </div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("<div style='clear:both;'></div>", unsafe_allow_html=True)


def _send_parent_message(text: str):
    if hate_model.is_enabled():
        with st.spinner("🤖 AI가 메시지를 분석하고 있어요..."):
            analysis = analyze_message(text, use_model=True)
    else:
        analysis = analyze_message(text, use_model=True)
    now = now_kst().strftime("%H:%M")
    blurred = blur_text(text) if analysis["is_profanity"] else text
    blocked = analysis["emotion_level"] >= 4

    room_id = st.session_state.get("teacher_room_id")
    msg = {
        "role": "parent",
        "text": text,
        "blurred_text": blurred,
        "blocked": blocked,
        "analysis": analysis,
        "emotion_level": analysis["emotion_level"],
        "timestamp": now,
        "user_id": st.session_state.user_id,
        "room_id": room_id,
    }
    st.session_state.chat_messages.append(msg)

    if analysis["is_profanity"]:
        st.session_state.archive.append({**msg, "archived_at": now_kst().isoformat()})
        st.session_state.stats["profanity"] += 1
        for t in analysis["types_detected"]:
            if t in st.session_state.stats["types"]:
                st.session_state.stats["types"][t] += 1

    st.session_state.stats["total"] += 1

    recent = st.session_state.chat_messages[-5:]
    levels = [m.get("emotion_level", 1) for m in recent if m["role"] == "parent"]
    st.session_state.current_emotion = max(levels) if levels else 1

    ai_msg = {
        "role": "ai",
        "text": get_auto_response(analysis),
        "timestamp": now,
        "room_id": room_id,
    }
    st.session_state.chat_messages.append(ai_msg)

    # DB 저장 (실패해도 session_state는 이미 갱신되어 있어 앱은 정상 동작)
    auth_user = st.session_state.get("auth_user") or {}
    auth_id = auth_user.get("user_id")
    if auth_id and db.is_enabled():
        db.insert_message(auth_id, msg, room_id=room_id)
        db.insert_message(auth_id, ai_msg, room_id=room_id)


def _send_teacher_reply(text: str):
    """교사가 학부모에게 직접 보내는 답장. room_id = 교사 본인 user_id."""
    now = now_kst().strftime("%H:%M")
    auth_user = st.session_state.get("auth_user") or {}
    auth_id = auth_user.get("user_id")
    msg = {
        "role": "teacher",
        "text": text,
        "timestamp": now,
        "user_id": st.session_state.user_id,
        "room_id": auth_id,  # 교사의 방 = 교사 본인 ID
    }
    st.session_state.chat_messages.append(msg)

    if auth_id and db.is_enabled():
        db.insert_message(auth_id, msg, room_id=auth_id)


def _reload_messages_from_db():
    """DB에서 채팅/보관함을 다시 불러와 session_state를 갱신한다."""
    if not db.is_enabled():
        return
    _fetch_room = getattr(db, "fetch_room_messages", None)
    role = st.session_state.get("role")
    if _fetch_room:
        if role == "parent":
            room_id = st.session_state.get("teacher_room_id")
            if room_id:
                ok, msgs = _fetch_room(room_id)
                if ok:
                    st.session_state.chat_messages = msgs
        else:
            auth_id = (st.session_state.get("auth_user") or {}).get("user_id")
            if auth_id:
                ok, msgs = _fetch_room(auth_id)
                if ok:
                    st.session_state.chat_messages = msgs
    else:
        ok, msgs = db.fetch_messages(limit=200)
        if ok:
            st.session_state.chat_messages = msgs
    ok2, arc = db.fetch_archive()
    if ok2:
        st.session_state.archive = arc


# ============================================================
# 페이지 3: 교사 대시보드
# ============================================================
def page_teacher():
    col_h1, col_h2 = st.columns([4, 1])
    with col_h1:
        u = st.session_state.auth_user or {}
        school_nm = u.get("school_name", "")
        title = f"👩‍🏫 {school_nm + ' ' if school_nm else ''}교사 대시보드"
        st.markdown(f"### {title}")
        st.caption(now_kst().strftime("%Y-%m-%d %H:%M"))
    with col_h2:
        if st.button("🚪 나가기"):
            st.session_state.role = None
            st.rerun()

    # 초대코드 배너
    auth_id = (st.session_state.auth_user or {}).get("user_id")
    _get_code = getattr(db, "get_or_create_invite_code", None)
    if auth_id and db.is_enabled() and _get_code:
        ok_c, invite_code = _get_code(auth_id)
    else:
        ok_c, invite_code = False, "XXXXXX"
    st.info(
        f"📤 **내 초대코드: `{invite_code}`** — "
        "학부모에게 이 코드를 공유하면 이 채팅방에 입장할 수 있습니다.",
        icon="🔑",
    )

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

    # ── 학부모와 직접 대화 (쌍방대화) ───────────────────────────
    st.divider()
    col_t1, col_t2 = st.columns([4, 1])
    with col_t1:
        st.markdown("#### 💬 학부모와 대화")
    with col_t2:
        if st.button("🔄 새로고침", key="refresh_monitor", use_container_width=True):
            _reload_messages_from_db()
            st.rerun()

    if st.session_state.chat_messages:
        for m in st.session_state.chat_messages[-20:]:
            _render_chat_message(m)
    else:
        st.markdown(
            "<div style='text-align:center; color:#bbb; padding:20px;'>"
            "아직 학부모 메시지가 없습니다.</div>",
            unsafe_allow_html=True,
        )

    st.markdown("##### ✏️ 답장 보내기")
    teacher_reply = st.text_area(
        "답장 입력",
        placeholder="예) 안녕하세요 어머님, 말씀해주신 부분 확인했습니다. 내일 자세히 안내드리겠습니다.",
        height=90, key="teacher_reply_input", label_visibility="collapsed",
    )
    if st.button("📤 답장 전송", key="send_teacher_reply",
                 use_container_width=True, type="primary"):
        if teacher_reply.strip():
            _send_teacher_reply(teacher_reply.strip())
            st.rerun()
        else:
            st.warning("답장 내용을 입력해주세요.")


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
                target = msg.get("user_id", "")
                st.session_state.blocked_users.add(target)
                auth_user = st.session_state.get("auth_user") or {}
                if target and auth_user.get("user_id") and db.is_enabled():
                    db.add_blocked_user(auth_user["user_id"], target)
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
            incident_date   = st.date_input("신고 날짜", now_kst())
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
            file_name=f"교권침해_신고서_{now_kst().strftime('%Y%m%d')}.txt",
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
  * 생성 일시 : {now_kst().strftime('%Y-%m-%d %H:%M:%S')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


# ============================================================
# 메인
# ============================================================
def main():
    apply_styles()
    init_session()

    # 1) 로그인 안 됐으면 인증 화면
    if st.session_state.auth_user is None:
        page_auth()
        return

    # 2) 로그인 직후 DB → session_state 1회 동기화
    _hydrate_from_db()

    # 3) 사이드바 — 사용자 정보 / 로그아웃
    with st.sidebar:
        u = st.session_state.auth_user
        st.markdown(f"### 👤 {u.get('display_name') or u.get('email')}")
        st.caption(u.get("email", ""))

        # 학교 정보 표시 (교사)
        school_nm = u.get("school_name", "")
        if school_nm:
            st.info(f"🏫 {u.get('school_region','')} {school_nm}")
        elif st.session_state.get("role") == "teacher":
            if st.button("🏫 학교 설정", use_container_width=True, key="sb_school_btn"):
                st.session_state.school_selected = False
                st.rerun()

        st.divider()
        if db.is_enabled():
            st.success("🟢 Supabase 연결됨")
        else:
            st.info("⚪ 게스트 모드 (로컬 세션)")
        if hate_model.is_enabled():
            st.success("🤖 AI 탐지 활성")
        else:
            st.warning("🔑 AI 탐지 비활성 (HF 토큰 필요)")
        if schools.is_api_enabled():
            st.success("🔎 NEIS 학교 검색 활성")

        st.divider()
        if st.button("🚪 로그아웃", use_container_width=True):
            db.sign_out()
            for k in ["auth_user", "role", "user_id", "chat_messages",
                      "archive", "blocked_users", "current_emotion",
                      "stats", "db_loaded", "school_selected",
                      "teacher_room_id", "teacher_info"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

    # 4) 역할 선택 → 각 페이지
    role = st.session_state.role
    if role is None:
        page_home()
    elif role == "parent":
        # 교사 방에 연결됐는지 확인
        if not st.session_state.get("teacher_room_id"):
            page_parent_connect()
        else:
            page_parent()
    elif role == "teacher":
        # 교사 첫 로그인 시 학교 선택 단계 삽입
        if not st.session_state.get("school_selected"):
            page_school_select()
        else:
            page_teacher()


if __name__ == "__main__":
    main()
