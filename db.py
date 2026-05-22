"""
티쳐가드 — Supabase 연동 모듈
=================================================
- 인증(회원가입/로그인/로그아웃)
- 메시지 저장/조회
- 보관함(부적절 메시지) 조회
- 차단 사용자 관리

설정이 안 되어 있거나 네트워크/RLS 오류가 나도 앱이 죽지 않도록
모든 함수가 (ok, data_or_error) 튜플을 반환하며,
DB가 없을 때는 호출 측에서 session_state 폴백을 그대로 사용합니다.
"""
from __future__ import annotations

from typing import Any, Optional

import streamlit as st

try:
    from supabase import Client, create_client  # type: ignore
except Exception:  # supabase-py 미설치
    Client = None  # type: ignore
    create_client = None  # type: ignore


# ============================================================
# 클라이언트 초기화 (캐시)
# ============================================================
@st.cache_resource(show_spinner=False)
def get_client() -> Optional["Client"]:
    """secrets.toml 의 supabase 섹션을 읽어 클라이언트를 만든다.
    설정이 없으면 None 반환 — 호출 측에서 폴백 처리.
    """
    if create_client is None:
        return None
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["anon_key"]
    except Exception:
        return None
    if not url or not key or url.startswith("YOUR_"):
        return None
    try:
        return create_client(url, key)
    except Exception:
        return None


def is_enabled() -> bool:
    return get_client() is not None


# ============================================================
# 인증
# ============================================================
def sign_up(email: str, password: str, display_name: str = "") -> tuple[bool, str]:
    client = get_client()
    if client is None:
        return False, "Supabase가 설정되지 않았습니다. SUPABASE_SETUP.md를 확인하세요."
    try:
        resp = client.auth.sign_up({
            "email": email,
            "password": password,
            "options": {"data": {"display_name": display_name or email.split("@")[0]}},
        })
        if resp.user is None:
            return False, "가입에 실패했습니다. 이메일/비밀번호를 다시 확인해주세요."
        return True, "가입 완료! 이메일 인증이 필요할 수 있습니다."
    except Exception as e:
        return False, f"가입 오류: {e}"


def sign_in(email: str, password: str) -> tuple[bool, Any]:
    client = get_client()
    if client is None:
        return False, "Supabase가 설정되지 않았습니다."
    try:
        resp = client.auth.sign_in_with_password({"email": email, "password": password})
        if resp.user is None or resp.session is None:
            return False, "로그인 실패: 이메일 또는 비밀번호를 확인해주세요."
        return True, {
            "user_id": resp.user.id,
            "email": resp.user.email,
            "access_token": resp.session.access_token,
        }
    except Exception as e:
        return False, f"로그인 오류: {e}"


def sign_out() -> None:
    client = get_client()
    if client is None:
        return
    try:
        client.auth.sign_out()
    except Exception:
        pass


# ============================================================
# 프로필 (학교 정보 등)
# ============================================================
def fetch_profile(user_id: str) -> tuple[bool, dict]:
    """profiles 테이블에서 user_id 에 해당하는 프로필 반환."""
    client = get_client()
    if client is None:
        return False, {}
    try:
        resp = (
            client.table("profiles")
            .select("*")
            .eq("id", user_id)
            .single()
            .execute()
        )
        return True, resp.data or {}
    except Exception:
        return False, {}


def update_profile(user_id: str, **fields) -> tuple[bool, Any]:
    """profiles 테이블의 school_region / school_type / school_name 등 업데이트."""
    client = get_client()
    if client is None:
        return False, "DB 미설정"
    if not fields:
        return True, {}
    try:
        resp = (
            client.table("profiles")
            .update(fields)
            .eq("id", user_id)
            .execute()
        )
        return True, resp.data
    except Exception as e:
        return False, str(e)


# ============================================================
# 메시지
# ============================================================
def insert_message(user_id: str, msg: dict) -> tuple[bool, Any]:
    """msg 는 streamlit_app 에서 만든 dict 그대로.
    sender_role 은 msg['role'] 을 사용.
    """
    client = get_client()
    if client is None:
        return False, "DB 미설정"
    try:
        analysis = msg.get("analysis", {}) or {}
        row = {
            "user_id": user_id,
            "sender_role": msg.get("role", "parent"),
            "text": msg.get("text", ""),
            "blurred_text": msg.get("blurred_text"),
            "blocked": bool(msg.get("blocked", False)),
            "is_profanity": bool(analysis.get("is_profanity", False)),
            "emotion_level": int(msg.get("emotion_level", analysis.get("emotion_level", 1))),
            "severity": int(analysis.get("severity", 1)),
            "types_detected": analysis.get("types_detected", []),
            "detected_keywords": analysis.get("detected_keywords", []),
            "display_time": msg.get("timestamp"),
        }
        resp = client.table("messages").insert(row).execute()
        return True, resp.data
    except Exception as e:
        return False, str(e)


def fetch_messages(limit: int = 200) -> tuple[bool, list[dict]]:
    """최근 메시지 N건을 시간 오름차순으로 반환 (채팅 흐름에 맞게)."""
    client = get_client()
    if client is None:
        return False, []
    try:
        resp = (
            client.table("messages")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        rows = list(reversed(resp.data or []))
        return True, [_row_to_msg(r) for r in rows]
    except Exception:
        return False, []


def fetch_archive() -> tuple[bool, list[dict]]:
    """부적절 메시지(is_profanity = true)만 모아 보관함용으로 반환."""
    client = get_client()
    if client is None:
        return False, []
    try:
        resp = (
            client.table("messages")
            .select("*")
            .eq("is_profanity", True)
            .order("created_at", desc=False)
            .execute()
        )
        return True, [_row_to_msg(r) for r in (resp.data or [])]
    except Exception:
        return False, []


def _row_to_msg(row: dict) -> dict:
    """DB row → 앱에서 쓰던 dict 형태로 변환."""
    return {
        "role": row.get("sender_role", "parent"),
        "text": row.get("text", ""),
        "blurred_text": row.get("blurred_text") or row.get("text", ""),
        "blocked": bool(row.get("blocked", False)),
        "emotion_level": int(row.get("emotion_level", 1)),
        "timestamp": row.get("display_time") or "",
        "user_id": row.get("user_id", ""),
        "analysis": {
            "is_profanity": bool(row.get("is_profanity", False)),
            "types_detected": row.get("types_detected") or [],
            "severity": int(row.get("severity", 1)),
            "emotion_level": int(row.get("emotion_level", 1)),
            "detected_keywords": row.get("detected_keywords") or [],
            "etiquette_warning": None,
        },
        "archived_at": row.get("created_at"),
    }


# ============================================================
# 차단 사용자
# ============================================================
def add_blocked_user(teacher_id: str, blocked_user_id: str) -> tuple[bool, Any]:
    client = get_client()
    if client is None:
        return False, "DB 미설정"
    try:
        resp = (
            client.table("blocked_users")
            .insert({"teacher_id": teacher_id, "blocked_user_id": blocked_user_id})
            .execute()
        )
        return True, resp.data
    except Exception as e:
        return False, str(e)


def fetch_blocked_users(teacher_id: str) -> tuple[bool, set[str]]:
    client = get_client()
    if client is None:
        return False, set()
    try:
        resp = (
            client.table("blocked_users")
            .select("blocked_user_id")
            .eq("teacher_id", teacher_id)
            .execute()
        )
        return True, {r["blocked_user_id"] for r in (resp.data or [])}
    except Exception:
        return False, set()
